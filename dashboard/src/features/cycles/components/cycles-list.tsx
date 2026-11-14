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

/** The cycles of the flow from the most recent, in the pages of the API (R2.2.7). */
export const CyclesList = ({ flowId, page }: { flowId: string; page: number }) => {
  const cycles = useCycles(flowId, page);
  if (cycles.isPending) {
    return <Loading />;
  }
  if (cycles.isError) {
    return <ErrorMessage error={cycles.error} />;
  }
  return (
    <>
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
        hrefOf={(target) => paths.flowCycles.getHref(flowId, target)}
      />
    </>
  );
};
