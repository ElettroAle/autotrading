import { useSearchParams } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import {
  isComplete,
  listIntervalOf,
  usePeriod,
  type ListInterval,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatInstant } from '@/utils/format-instant';
import { searchWithPage } from '@/utils/page-number';

import { useCycles, type CycleSummary } from '../api/get-cycles';
import { decisionLabelsOf } from '../utils/cycle-documents';

const NO_DECISION = '—';

// The values are those the API accepts (R6.4.4).
const CYCLE_FILTERS: readonly TableFilter[] = [
  {
    name: 'outcome',
    label: 'Esito',
    all: 'Tutti',
    options: [
      { value: 'concluso', label: 'Conclusi' },
      { value: 'fallito', label: 'Falliti' },
    ],
  },
  {
    name: 'decision',
    label: 'Decisione',
    all: 'Tutte',
    options: [
      { value: 'apertura', label: 'Aperture' },
      { value: 'chiusura', label: 'Chiusure' },
      { value: 'mantenimento', label: 'Mantenimenti' },
      { value: 'nessuna', label: 'Nessuna decisione' },
    ],
  },
];

const emptyText = (filtered: boolean, interval: ListInterval): string => {
  if (filtered) {
    return 'Nessun ciclo con questi filtri.';
  }
  return interval.from === undefined
    ? 'Nessun ciclo registrato.'
    : 'Nessun ciclo nel periodo scelto.';
};

const countOf = (total: number): string => (total === 1 ? '1 ciclo' : `${total} cicli`);

const outcomeOf = (cycle: CycleSummary): string =>
  cycle.failure === null ? cycle.outcome : `${cycle.outcome} nel passo «${cycle.failure.step}»`;

const decisionsOf = (cycle: CycleSummary): string =>
  decisionLabelsOf(cycle.decisions).join(', ') || NO_DECISION;

const COLUMNS: DataTableColumn<CycleSummary>[] = [
  { header: 'Istante', cell: (cycle) => formatInstant(cycle.planned_at) },
  { header: 'Esito', cell: outcomeOf },
  { header: 'Decisioni', cell: decisionsOf },
];

type CyclesInIntervalProps = {
  readonly flowId: string;
  readonly page: number;
  readonly interval: ListInterval;
};

const CyclesInInterval = ({ flowId, page, interval }: CyclesInIntervalProps) => {
  const { values } = useTableFilters(CYCLE_FILTERS);
  const [search] = useSearchParams();
  const cycles = useCycles(flowId, page, values, interval);
  if (cycles.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (cycles.data === undefined) {
    return <ErrorMessage error={cycles.error} />;
  }
  const filtered = Object.keys(values).length > 0;
  return (
    <>
      <DataTable
        label="Cicli"
        columns={COLUMNS}
        rows={cycles.data.cycles}
        rowKey={(cycle) => cycle.planned_at}
        rowHref={(cycle) => paths.cycle.getHref(flowId, cycle.planned_at)}
        empty={emptyText(filtered, interval)}
        filtering={{ filters: CYCLE_FILTERS, total: cycles.data.total, countOf }}
      />
      <Pagination
        page={cycles.data.page}
        hasNext={cycles.data.has_next}
        hrefOf={(target) => `${paths.flowCycles.getHref(flowId)}${searchWithPage(search, target)}`}
      />
    </>
  );
};

/**
 * The cycles of the flow in the period of the page that match the filters of the address, from the most recent, in the
 * pages of the API; each row opens its cycle (R2.2.7, R6.4.4, R6.4.3).
 */
export const CyclesList = ({ flowId, page }: { flowId: string; page: number }) => {
  const [period] = usePeriod();
  if (!isComplete(period)) {
    return (
      <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>
    );
  }
  return (
    <CyclesInInterval flowId={flowId} page={page} interval={listIntervalOf(period, new Date())} />
  );
};
