import { periodAdmits, statisticsOf } from './flow-statistics';
import type { FakeFlow } from './platform';

// A draft has never run and an archived flow is over: neither competes (R2.4.2).
const OUT_OF_RANKING = ['archiviato', 'bozza'];

const returnOf = (curve: number[]): string | null => {
  const first = curve[0] ?? 0;
  const last = curve.at(-1) ?? 0;
  return first <= 0 ? null : (((last - first) / first) * 100).toFixed(2);
};

const maxDrawdownOf = (curve: number[]): string => {
  let peak = 0;
  let deepest = 0;
  for (const equity of curve) {
    peak = Math.max(peak, equity);
    if (peak > 0) {
      deepest = Math.max(deepest, ((peak - equity) / peak) * 100);
    }
  }
  return deepest.toFixed(2);
};

const rowOf = (flow: FakeFlow, curve: number[], search: URLSearchParams, now: number) => {
  const admits = periodAdmits(search, now);
  const statistics = statisticsOf(flow.history, search, now);
  const pnl = flow.history.closedPositions
    .filter((position) => admits(position.closedAt))
    .reduce((total, position) => total + position.netPnl, 0);
  return {
    flow_id: flow.id,
    flow_name: flow.name,
    return_percent: returnOf(curve),
    max_drawdown_percent: maxDrawdownOf(curve),
    pnl: String(pnl),
    total_fees: statistics.total_fees,
    win_rate_percent: statistics.win_rate_percent,
    operations: statistics.operations,
    model_cost_usd: statistics.model_cost_usd,
    model_calls_without_cost: statistics.model_calls_without_cost,
  };
};

type Row = ReturnType<typeof rowOf>;

// From the highest return, the flows without one last, the name breaking a tie, as the API orders them (ADR 0135).
const byReturn = (one: Row, other: Row): number => {
  if (one.return_percent === null || other.return_percent === null) {
    return Number(one.return_percent === null) - Number(other.return_percent === null);
  }
  return (
    Number(other.return_percent) - Number(one.return_percent) ||
    one.flow_name.localeCompare(other.flow_name)
  );
};

/**
 * The ranking of the flows as the API computes it (R2.4.2): the flows neither drafts nor archived with a cycle in the period, the
 * return and the drawdown on their equity, the statistics of the same period; a period it rejects throws.
 */
export const rankingOf = (flows: FakeFlow[], search: URLSearchParams, now = Date.now()) => {
  const admits = periodAdmits(search, now);
  return flows
    .filter((flow) => !OUT_OF_RANKING.includes(flow.status))
    .map((flow) => ({
      flow,
      curve: flow.equity
        .filter((point) => admits(point.plannedAt))
        .toSorted((first, second) => first.plannedAt.getTime() - second.plannedAt.getTime())
        .map((point) => point.equity),
    }))
    .filter(({ curve }) => curve.length > 0)
    .map(({ flow, curve }) => rowOf(flow, curve, search, now))
    .toSorted(byReturn);
};
