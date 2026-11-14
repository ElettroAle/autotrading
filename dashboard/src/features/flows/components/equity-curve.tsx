import { EquityChart } from '@/components/charts/equity-chart';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isComplete, usePeriod, type Period } from '@/components/ui/period-selector/use-period';

import { useFlowEquity } from '../api/get-flow-equity';

const EquityPoints = ({ flowId, period }: { flowId: string; period: Period }) => {
  const equity = useFlowEquity(flowId, period);
  if (equity.isPending) {
    return <Loading />;
  }
  if (equity.isError) {
    return <ErrorMessage error={equity.error} />;
  }
  if (equity.data.points.length > 0) {
    return <EquityChart points={equity.data.points} baseline={equity.data.initialCapital} />;
  }
  return (
    <p className="text-slate-600">
      {period.kind === 'all' ? 'Nessun ciclo ancora eseguito' : 'Nessun ciclo nel periodo scelto'}
    </p>
  );
};

/** The equity curve of the flow in the period of the page, shared with the other panels (R2.2.3, ADR 0123). */
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
        <p className="text-slate-600">
          Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.
        </p>
      )}
    </section>
  );
};
