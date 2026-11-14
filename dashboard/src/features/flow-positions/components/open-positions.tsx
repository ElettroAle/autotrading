import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatAmount } from '@/utils/format-amount';

import { useFlowState, type OpenPosition } from '../api/get-flow-state';

import { PnlAmount, PnlPercent } from './pnl';

const columnsIn = (currency: string): DataTableColumn<OpenPosition>[] => [
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => position.side },
  { header: 'Dimensione', cell: (position) => formatAmount(position.size) },
  { header: 'Leva', cell: (position) => position.leverage },
  { header: 'Prezzo di ingresso', cell: (position) => formatAmount(position.entry_price) },
  { header: 'Margine', cell: (position) => `${formatAmount(position.margin)} ${currency}` },
  {
    header: 'PnL',
    cell: (position) => <PnlAmount amount={position.unrealized_pnl} unit={currency} />,
  },
  { header: 'PnL %', cell: (position) => <PnlPercent percent={position.unrealized_pnl_percent} /> },
];

/** The positions the flow holds now, as the exchange shows them through the state of the flow (R2.2.4). */
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
      empty="Nessuna posizione aperta."
    />
  );
};
