import { Link, useSearchParams } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { DirectionLabel } from '@/components/ui/direction-label';
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
import { useFlowAssets } from '@/hooks/use-flow-assets';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatAmount, formatPrice } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';
import { searchWithPage } from '@/utils/page-number';

import { useClosedPositions, type ClosedPosition } from '../api/get-closed-positions';
import { useFlowState } from '../api/get-flow-state';

import { PnlAmount, PnlPercent } from './pnl';

const inUnit = (amount: string, unit: string | undefined): string =>
  unit === undefined ? formatAmount(amount) : `${formatAmount(amount)} ${unit}`;

const columnsIn = (currency: string | undefined): DataTableColumn<ClosedPosition>[] => [
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => <DirectionLabel value={position.side} /> },
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

const emptyText = (filtered: boolean, interval: ListInterval): string => {
  if (filtered) {
    return 'Nessuna posizione chiusa con questi filtri.';
  }
  return interval.from === undefined
    ? 'Nessuna posizione chiusa.'
    : 'Nessuna posizione chiusa nel periodo scelto.';
};

/** The closing a notification points at, by asset and instant (ADR posizione-evidenziata-dall-indirizzo). */
type NotifiedClosing = { readonly asset: string; readonly closedAt: number };

const notifiedClosingOf = (search: URLSearchParams): NotifiedClosing | undefined => {
  const asset = search.get('asset');
  const closedAt = Date.parse(search.get('closed_at') ?? '');
  return asset === null || Number.isNaN(closedAt) ? undefined : { asset, closedAt };
};

const isNotified = (position: ClosedPosition, closing: NotifiedClosing | undefined): boolean =>
  closing !== undefined &&
  position.asset === closing.asset &&
  Date.parse(position.closed_at) === closing.closedAt;

// The tab shows one page: an older closing is in the history, narrowed to the flow and the asset.
const historyHrefOf = (flowId: string, asset: string): string =>
  `${paths.history.getHref()}?${new URLSearchParams({ tab: 'closed-positions', flow: flowId, asset }).toString()}`;

const ClosingNotOnThePage = ({ flowId, asset }: { flowId: string; asset: string }) => (
  <p role="status" className="mb-3 rounded border border-amber-300 bg-amber-50 p-2 text-sm">
    L&apos;operazione della notifica non è in questa pagina.{' '}
    <Link to={historyHrefOf(flowId, asset)} className="font-medium text-blue-800 hover:underline">
      Cercala nello Storico
    </Link>
  </p>
);

type PositionsInIntervalProps = {
  readonly flowId: string;
  readonly page: number;
  readonly interval: ListInterval;
};

/**
 * The closed positions of the flow that match the filters of the address, from the most recent close, in the pages of
 * the API (R2.2.5, R6.4.4). The currency comes from the state of the flow, read from the exchange: without it the
 * amounts still show, the history does not depend on the exchange (ADR 0143).
 */
const PositionsInInterval = ({ flowId, page, interval }: PositionsInIntervalProps) => {
  const filters = filtersFor(useFlowAssets(flowId).data ?? []);
  const { values } = useTableFilters(filters);
  const [search] = useSearchParams();
  const positions = useClosedPositions(flowId, page, values, interval);
  const currency = useFlowState(flowId).data?.currency;
  if (positions.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (positions.data === undefined) {
    return <ErrorMessage error={positions.error} />;
  }
  const filtered = Object.keys(values).length > 0;
  const notified = notifiedClosingOf(search);
  const rows = positions.data.positions;
  return (
    <>
      {notified !== undefined && !rows.some((position) => isNotified(position, notified)) && (
        <ClosingNotOnThePage flowId={flowId} asset={notified.asset} />
      )}
      <DataTable
        label="Posizioni chiuse"
        columns={columnsIn(currency)}
        rows={rows}
        rowKey={(position) => `${position.closed_at}-${position.asset}`}
        highlightedRow={(position) => isNotified(position, notified)}
        empty={emptyText(filtered, interval)}
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
    return <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>;
  }
  return (
    <PositionsInInterval
      flowId={flowId}
      page={page}
      interval={listIntervalOf(period, new Date())}
    />
  );
};
