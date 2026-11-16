import type { FakeCycle } from './cycles';
import { contains, windowOf } from './flow-statistics';
import type { FakeFlow } from './platform';

const FAILED = 'fallito';

// The API writes amounts without trailing zeros (ADR 0018); the fake rounds away the noise of binary numbers first.
const amountText = (amount: number): string => String(Number(amount.toFixed(8)));

// A percent of the initial capital with two decimals, absent without initial capital, as the domain measures it.
const percentText = (amount: number, initial: number): string | null =>
  initial === 0 ? null : ((amount / initial) * 100).toFixed(2);

/**
 * The summary of the results of a flow as the API answers it for the period of the request (R6.4.2): the gain in all
 * from the capital, the gain in the period from the first to the last equity recorded in it, the open positions and the
 * failed cycles of the period. A period the API rejects throws.
 */
export const resultsOf = (
  flow: FakeFlow,
  cycles: readonly FakeCycle[],
  openPositions: number,
  search: URLSearchParams,
  now = Date.now(),
) => {
  const window = windowOf(search, now);
  const initial = flow.allocatedCapital ?? 0;
  const totalGain = flow.currentCapital - initial;
  const equity = flow.equity
    .filter((point) => contains(window, point.plannedAt))
    .toSorted((first, second) => first.plannedAt.getTime() - second.plannedAt.getTime());
  const periodGain = (equity.at(-1)?.equity ?? 0) - (equity[0]?.equity ?? 0);
  return {
    total_gain: amountText(totalGain),
    total_gain_percent: percentText(totalGain, initial),
    period_gain: amountText(periodGain),
    period_gain_percent: percentText(periodGain, initial),
    open_positions: openPositions,
    failed_cycles: cycles.filter(
      (cycle) => cycle.outcome === FAILED && contains(window, new Date(cycle.planned_at)),
    ).length,
  };
};
