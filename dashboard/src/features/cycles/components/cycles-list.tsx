import { Link } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import { paths } from '@/config/paths';
import { formatInstant } from '@/utils/format-instant';

import { useCycles, type CycleSummary } from '../api/get-cycles';
import { decisionLabelsOf } from '../utils/cycle-documents';

const NO_DECISION = '—';

const outcomeOf = (cycle: CycleSummary): string =>
  cycle.failure === null ? cycle.outcome : `${cycle.outcome} nel passo «${cycle.failure.step}»`;

const decisionsOf = (cycle: CycleSummary): string =>
  decisionLabelsOf(cycle.decisions).join(', ') || NO_DECISION;

const columnsFor = (flowId: string): DataTableColumn<CycleSummary>[] => [
  {
    header: 'Istante',
    cell: (cycle) => (
      <Link
        to={paths.cycle.getHref(flowId, cycle.planned_at)}
        className="font-medium text-blue-800 hover:underline"
      >
        {formatInstant(cycle.planned_at)}
      </Link>
    ),
  },
  { header: 'Esito', cell: outcomeOf },
  { header: 'Decisioni', cell: decisionsOf },
];

type CyclesListProps = {
  readonly flowId: string;
  readonly page: number;
  /** The outcome the cycles are filtered on, empty for every cycle (R6.4.2). */
  readonly outcome?: string;
};

// The filter the failed cycles of the summary of the results lead to, said above the cycles with a way back (R6.4.2).
const OutcomeFilter = ({ flowId, outcome }: { flowId: string; outcome: string }) => (
  <p className="mb-2 flex flex-wrap gap-2 text-sm text-slate-700">
    <span>{`Solo i cicli ${outcome === 'fallito' ? 'falliti' : `con esito «${outcome}»`}.`}</span>
    <Link to={paths.flowCycles.getHref(flowId)} className="text-blue-800 hover:underline">
      Mostra tutti i cicli
    </Link>
  </p>
);

/** The cycles of the flow from the most recent, in the pages of the API (R2.2.7), filtered on an outcome if asked. */
export const CyclesList = ({ flowId, page, outcome = '' }: CyclesListProps) => {
  const cycles = useCycles(flowId, page, outcome);
  if (cycles.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (cycles.data === undefined) {
    return <ErrorMessage error={cycles.error} />;
  }
  return (
    <>
      {outcome === '' ? null : <OutcomeFilter flowId={flowId} outcome={outcome} />}
      <DataTable
        label="Cicli"
        columns={columnsFor(flowId)}
        rows={cycles.data.cycles}
        rowKey={(cycle) => cycle.planned_at}
        empty="Nessun ciclo registrato."
      />
      <Pagination
        page={cycles.data.page}
        hasNext={cycles.data.has_next}
        hrefOf={(target) => paths.flowCycles.getHref(flowId, target, outcome)}
      />
    </>
  );
};
