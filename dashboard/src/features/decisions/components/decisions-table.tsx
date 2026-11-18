import { useSearchParams } from 'react-router';

import { ActionLabel } from '@/components/ui/action-label';
import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { DirectionLabel } from '@/components/ui/direction-label';
import { ErrorMessage } from '@/components/ui/error-message';
import { ExpandableText } from '@/components/ui/expandable-text';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import { isComplete, usePeriod, type Period } from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { useFlowAssets } from '@/hooks/use-flow-assets';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatInstant } from '@/utils/format-instant';
import { searchWithPage } from '@/utils/page-number';

import { useDecisions, type DatedDecision } from '../api/list-decisions';

const NO_DIRECTION = '—';
const NOT_AVAILABLE = 'non disponibile';

// The values are those the API accepts; the assets are those of the flow (R6.5.5).
const filtersFor = (assets: readonly string[]): TableFilter[] => [
  {
    name: 'asset',
    label: 'Asset',
    all: 'Tutti',
    options: assets.map((asset) => ({ value: asset, label: asset })),
  },
  {
    name: 'action',
    label: 'Azione',
    all: 'Tutte',
    options: [
      { value: 'apri', label: 'Apri' },
      { value: 'chiudi', label: 'Chiudi' },
      { value: 'mantieni', label: 'Mantieni' },
      { value: 'aggiorna', label: 'Aggiorna' },
      { value: 'inverti', label: 'Inverti' },
    ],
  },
  {
    name: 'direction',
    label: 'Direzione',
    all: 'Tutte',
    options: [
      { value: 'long', label: 'Long' },
      { value: 'short', label: 'Short' },
    ],
  },
];

// The values are the API's: the table shortens the reasoning, which opens whole in its row (ADR testo-lungo-espandibile).
const COLUMNS: DataTableColumn<DatedDecision>[] = [
  { header: 'Istante', cell: (decision) => formatInstant(decision.planned_at) },
  { header: 'Asset', cell: (decision) => decision.asset },
  { header: 'Azione', cell: (decision) => <ActionLabel value={decision.action} /> },
  {
    header: 'Direzione',
    cell: (decision) =>
      decision.direction === null ? NO_DIRECTION : <DirectionLabel value={decision.direction} />,
  },
  {
    header: 'Confidenza',
    cell: (decision) =>
      decision.confidence === null ? NOT_AVAILABLE : String(decision.confidence),
  },
  {
    header: 'Ragionamento',
    cell: (decision) => <ExpandableText text={decision.reasoning} />,
  },
];

const countOf = (total: number): string => (total === 1 ? '1 decisione' : `${total} decisioni`);

const emptyText = (filtered: boolean, period: Period): string => {
  if (filtered) {
    return 'Nessuna decisione con questi filtri.';
  }
  return period.kind === 'all'
    ? 'Nessuna decisione registrata.'
    : 'Nessuna decisione nel periodo scelto.';
};

type DecisionsInPeriodProps = {
  readonly flowId: string;
  readonly page: number;
  readonly period: Period;
};

const DecisionsInPeriod = ({ flowId, page, period }: DecisionsInPeriodProps) => {
  const filters = filtersFor(useFlowAssets(flowId).data ?? []);
  const { values } = useTableFilters(filters);
  const [search] = useSearchParams();
  const decisions = useDecisions(flowId, page, values, period);
  if (decisions.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (decisions.data === undefined) {
    return <ErrorMessage error={decisions.error} />;
  }
  const filtered = Object.keys(values).length > 0;
  return (
    <>
      <DataTable
        label="Decisioni"
        columns={COLUMNS}
        rows={decisions.data.decisions}
        rowKey={(decision) => `${decision.planned_at}-${decision.asset}`}
        rowHref={(decision) => paths.cycle.getHref(flowId, decision.planned_at)}
        empty={emptyText(filtered, period)}
        filtering={{ filters, total: decisions.data.total, countOf }}
      />
      <Pagination
        page={decisions.data.page}
        hasNext={decisions.data.has_next}
        hrefOf={(target) =>
          `${paths.flowDecisions.getHref(flowId)}${searchWithPage(search, target)}`
        }
      />
    </>
  );
};

/**
 * The decisions of the agent in the flow in the period of the page, one row per cycle and asset, as the filters of the
 * address narrow them; each row opens the detail of its cycle (R6.5.5, ADR scheda-decisioni-nella-pagina-del-flusso).
 */
export const DecisionsTable = ({ flowId, page }: { flowId: string; page: number }) => {
  const [period] = usePeriod();
  if (!isComplete(period)) {
    return <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>;
  }
  return <DecisionsInPeriod flowId={flowId} page={page} period={period} />;
};
