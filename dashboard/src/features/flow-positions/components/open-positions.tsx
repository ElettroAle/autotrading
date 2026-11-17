import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';
import { DirectionLabel } from '@/components/ui/direction-label';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatAmount, formatPrice } from '@/utils/format-amount';

import { useFlowState, type OpenPosition } from '../api/get-flow-state';

import { PnlAmount, PnlPercent } from './pnl';

const NONE = '—';

const priceOrNone = (price: string | null): string => (price === null ? NONE : formatPrice(price));

const columnsIn = (currency: string): DataTableColumn<OpenPosition>[] => [
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => <DirectionLabel value={position.side} /> },
  { header: 'Dimensione', cell: (position) => formatAmount(position.size) },
  { header: 'Leva', cell: (position) => position.leverage },
  { header: 'Prezzo di ingresso', cell: (position) => formatPrice(position.entry_price) },
  { header: 'Obiettivo', cell: (position) => priceOrNone(position.target_price) },
  { header: 'Stop', cell: (position) => priceOrNone(position.stop_price) },
  { header: 'Margine', cell: (position) => `${formatAmount(position.margin)} ${currency}` },
  {
    header: 'PnL',
    cell: (position) => <PnlAmount amount={position.unrealized_pnl} unit={currency} />,
  },
  { header: 'PnL %', cell: (position) => <PnlPercent percent={position.unrealized_pnl_percent} /> },
];

// The condition that invalidates the opening is a text of the agent: it wraps under the position (R3.1.1).
const invalidationOf = ({ invalidation }: OpenPosition) =>
  invalidation === null ? undefined : (
    <dl className={DETAILS_GRID}>
      <dt className="font-medium text-slate-600">Invalidazione</dt>
      <dd className={DETAIL_VALUE}>{invalidation}</dd>
    </dl>
  );

/**
 * The positions the flow holds now, as the exchange shows them through the state of the flow (R2.2.4), with the exit
 * plan in force of each (ADR piano-di-uscita-nella-dashboard).
 */
export const OpenPositions = ({ flowId }: { flowId: string }) => {
  const state = useFlowState(flowId);
  if (state.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (state.data === undefined) {
    return <ErrorMessage error={state.error} />;
  }
  return (
    <DataTable
      label="Posizioni aperte"
      columns={columnsIn(state.data.currency)}
      rows={state.data.positions}
      rowKey={(position) => position.asset}
      rowDetail={invalidationOf}
      empty="Nessuna posizione aperta."
    />
  );
};
