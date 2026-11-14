import { ComparisonChart, type ComparedSeries } from '@/components/charts/comparison-chart';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isComplete, usePeriod, type Period } from '@/components/ui/period-selector/use-period';

import { useComparedEquities } from '../api/get-compared-equities';
import { useComparedFlowIds } from '../hooks/use-compared-flow-ids';

/** A flow the user can compare: the name is what the legend shows. */
export type ComparableFlow = { readonly id: string; readonly name: string };

const ComparedCurves = ({
  flows,
  period,
}: {
  flows: readonly ComparableFlow[];
  period: Period;
}) => {
  const equities = useComparedEquities(
    flows.map((flow) => flow.id),
    period,
  );
  // A failed rereading keeps the curves already read on the page: the warning is the page's (ADR 0119).
  const [error] = equities.flatMap((equity) =>
    equity.error === null || equity.data !== undefined ? [] : [equity.error],
  );
  if (error !== undefined) {
    return <ErrorMessage error={error} />;
  }
  if (equities.some((equity) => equity.isPending)) {
    return <Loading />;
  }
  const series: ComparedSeries[] = flows.map((flow, index) => ({
    ...flow,
    points: equities[index]?.data ?? [],
  }));
  if (series.every((flow) => flow.points.length === 0)) {
    return <p className="text-slate-600">Nessun ciclo nel periodo scelto</p>;
  }
  return <ComparisonChart series={series} />;
};

/**
 * The equity curves of the flows chosen in the ranking, on the same chart and over the period of the page
 * (R2.4.3, ADR 0137). A flow the user does not have is not compared.
 */
export const EquityComparison = ({ flows }: { flows: readonly ComparableFlow[] }) => {
  const [period] = usePeriod();
  const chosen = useComparedFlowIds().flatMap((flowId) =>
    flows.filter((flow) => flow.id === flowId),
  );
  if (chosen.length === 0) {
    return (
      <p className="text-slate-600">Scegli da 1 a 5 flussi dalla classifica da confrontare.</p>
    );
  }
  if (!isComplete(period)) {
    return (
      <p className="text-slate-600">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  return <ComparedCurves flows={chosen} period={period} />;
};
