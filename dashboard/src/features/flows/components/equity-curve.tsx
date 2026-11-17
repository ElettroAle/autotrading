import { EquityChart, type ChartEvent } from '@/components/charts/equity-chart';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import {
  intervalOfInstants,
  isComplete,
  listIntervalOf,
  usePeriod,
  usePeriodInterval,
  type Period,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import { useCapitalChangeMarks, type CapitalChangeMark } from '../api/get-capital-change-marks';
import { useFailedCycles } from '../api/get-failed-cycles';
import { useFlowEquity } from '../api/get-flow-equity';

// Each failed cycle is a red cross that leads to its detail (ADR cicli-falliti-sull-equity-curve).
const failedCycleEvent = (flowId: string, plannedAt: string): ChartEvent => ({
  kind: 'failed-cycle',
  instant: plannedAt,
  label: `Ciclo fallito del ${formatInstant(plannedAt)}`,
  to: paths.cycle.getHref(flowId, plannedAt),
});

// Each change of the capital is marked with its reason and amount, and leads to the history of the capital (ADR
// rendimento-composto-tra-le-variazioni-di-capitale).
const capitalChangeEvent = (flowId: string, change: CapitalChangeMark): ChartEvent => ({
  kind: 'capital-change',
  instant: change.changedAt,
  label: `${change.reason}, ${formatAmount(change.amount)} ${change.currency}`,
  to: paths.flowCapital.getHref(flowId),
});

const EquityPoints = ({ flowId, period }: { flowId: string; period: Period }) => {
  const equity = useFlowEquity(flowId, period);
  const interval = listIntervalOf(period, new Date());
  const failed = useFailedCycles(flowId, interval);
  const changes = useCapitalChangeMarks(flowId, interval);
  const { chooseInterval } = usePeriodInterval();
  if (equity.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (equity.data === undefined) {
    return <ErrorMessage error={equity.error} />;
  }
  // A draft has no capital and no cycle yet (ADR 0124): it shows no curve.
  const { points, initialCapital } = equity.data;
  return (
    <EquityChart
      points={initialCapital === null ? [] : points}
      baseline={initialCapital ?? 0}
      events={[
        ...(failed.data ?? []).map((plannedAt) => failedCycleEvent(flowId, plannedAt)),
        ...(changes.data ?? []).map((change) => capitalChangeEvent(flowId, change)),
      ]}
      onSelect={(from, to) => chooseInterval(intervalOfInstants(from, to))}
      {...(period.kind === 'all' ? { empty: 'Nessun ciclo ancora eseguito' } : {})}
    />
  );
};

/**
 * The equity curve of the flow in the period of the page, shared with the other panels (R2.2.3, ADR 0123): a drag on
 * it chooses an interval for the whole page (ADR intervallo-trascinando-sull-equity-curve), its failed cycles are red
 * crosses (ADR cicli-falliti-sull-equity-curve), its changes of the capital are marked with reason and amount (ADR
 * rendimento-composto-tra-le-variazioni-di-capitale).
 */
export const EquityCurve = ({ flowId }: { flowId: string }) => {
  const [period] = usePeriod();
  return (
    <section
      aria-labelledby="equity-curve"
      className="mt-4 rounded border border-slate-200 bg-white p-4"
    >
      <h3 id="equity-curve" className="mb-3 text-lg font-semibold">
        Equity curve
      </h3>
      {isComplete(period) ? (
        <EquityPoints flowId={flowId} period={period} />
      ) : (
        <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>
      )}
    </section>
  );
};
