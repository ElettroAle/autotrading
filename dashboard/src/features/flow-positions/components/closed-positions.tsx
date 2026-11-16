import { useSearchParams } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import {
  isComplete,
  listDaysOf,
  usePeriod,
  type ListDays,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatAmount, formatPrice } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';
import { searchWithPage } from '@/utils/page-number';

import { useClosedPositions, type ClosedPosition } from '../api/get-closed-positions';
import { useFlowAssets } from '../api/get-flow-assets';
import { useFlowState } from '../api/get-flow-state';

import { PnlAmount, PnlPercent } from './pnl';

const inUnit = (amount: string, unit: string | undefined): string =>
  unit === undefined ? formatAmount(amount) : `${formatAmount(amount)} ${unit}`;

const columnsIn = (currency: string | undefined): DataTableColumn<ClosedPosition>[] => [
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => position.side },
  { header: 'Aperta il', cell: (position) => formatInstant(position.opened_at) },
  { header: 'Apertura', cell: (position) => formatPrice(position.open_price) },
  { header: 'Chiusa il', cell: (position) => formatInstant(position.closed_at) },
  { header: 'Chiusura', cell: (position) => formatPrice(position.close_price) },
  { header: 'PnL', cell: (position) => <PnlAmount amount={position.pnl} unit={currency} /> },
  { header: 'PnL %', cell: (position) => <PnlPercent percent={position.pnl_percent_of_margin} /> },
  { header: 'Commissioni', cell: (position) => inUnit(position.fees, currency) },
  { header: 'Motivo', cell: (position) => position.reason },
];

// The values are those the API accepts; the assets are those of the flow (R6.4.4).
const filtersFor = (assets: readonly string[]): TableFilter[] => [
  {
    name: 'side',
    label: 'Direzione',
    all: 'Tutte',
    options: [
      { value: 'long', label: 'Long' },
      { value: 'short', label: 'Short' },
    ],
  },
  {
    name: 'result',
    label: 'Risultato',
    all: 'Tutte',
    options: [
      { value: 'vinta', label: 'Vinte' },
      { value: 'persa', label: 'Perse' },
    ],
  },
  {
    name: 'asset',
    label: 'Asset',
    all: 'Tutti',
    options: assets.map((asset) => ({ value: asset, label: asset })),
  },
];

const countOf = (total: number): string => (total === 1 ? '1 posizione' : `${total} posizioni`);

const emptyText = (filtered: boolean, days: ListDays): string => {
  if (filtered) {
    return 'Nessuna posizione chiusa con questi filtri.';
  }
  return days.from === undefined
    ? 'Nessuna posizione chiusa.'
    : 'Nessuna posizione chiusa nel periodo scelto.';
};

type PositionsInDaysProps = {
  readonly flowId: string;
  readonly page: number;
  readonly days: ListDays;
};

/**
 * The closed positions of the flow that match the filters of the address, from the most recent close, in the pages of
 * the API (R2.2.5, R6.4.4). The currency comes from the state of the flow, read from the exchange: without it the
 * amounts still show, the history does not depend on the exchange (ADR 0143).
 */
const PositionsInDays = ({ flowId, page, days }: PositionsInDaysProps) => {
  const filters = filtersFor(useFlowAssets(flowId).data ?? []);
  const { values } = useTableFilters(filters);
  const [search] = useSearchParams();
  const positions = useClosedPositions(flowId, page, values, days);
  const currency = useFlowState(flowId).data?.currency;
  if (positions.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (positions.data === undefined) {
    return <ErrorMessage error={positions.error} />;
  }
  const filtered = Object.keys(values).length > 0;
  return (
    <>
      <DataTable
        label="Posizioni chiuse"
        columns={columnsIn(currency)}
        rows={positions.data.positions}
        rowKey={(position) => `${position.closed_at}-${position.asset}`}
        empty={emptyText(filtered, days)}
        filtering={{ filters, total: positions.data.total, countOf }}
      />
      <Pagination
        page={positions.data.page}
        hasNext={positions.data.has_next}
        hrefOf={(target) =>
          `${paths.flowClosedPositions.getHref(flowId)}${searchWithPage(search, target)}`
        }
      />
    </>
  );
};

/** The closed positions of the flow in the period of the page (R6.4.3), as the filters of the address narrow them. */
export const ClosedPositions = ({ flowId, page }: { flowId: string; page: number }) => {
  const [period] = usePeriod();
  if (!isComplete(period)) {
    return (
      <p className="text-slate-600">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  return <PositionsInDays flowId={flowId} page={page} days={listDaysOf(period, new Date())} />;
};
