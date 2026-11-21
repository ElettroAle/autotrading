import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isComplete, usePeriod, type Period } from '@/components/ui/period-selector/use-period';

import { useFlowResults } from '../api/get-flow-results';

import { ResultsSummary } from './results-summary';

type ResultsProps = { readonly flowId: string; readonly archived: boolean };

const Results = ({ flowId, archived, period }: ResultsProps & { readonly period: Period }) => {
  const results = useFlowResults(flowId, period);
  if (results.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the results already read on the page: the warning is the page's (ADR 0119).
  if (results.data === undefined) {
    return <ErrorMessage error={results.error} />;
  }
  return (
    <ResultsSummary
      flowId={flowId}
      currency={results.data.currency}
      summary={results.data.summary}
      nextCycleAt={results.data.summary.next_cycle_at}
      archived={archived}
    />
  );
};

/** The summary of the results at the top of the page of the flow, in the period of the page, with the next cycle (R6.4.2,
 * R6.4.8). */
export const FlowResults = ({ flowId, archived }: ResultsProps) => {
  const [period] = usePeriod();
  if (!isComplete(period)) {
    return <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>;
  }
  return <Results flowId={flowId} archived={archived} period={period} />;
};
