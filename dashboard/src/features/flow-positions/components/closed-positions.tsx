import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import { paths } from '@/config/paths';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import { useClosedPositions, type ClosedPosition } from '../api/get-closed-positions';
import { useFlowState } from '../api/get-flow-state';

import { PnlAmount, PnlPercent } from './pnl';

const inUnit = (amount: string, unit: string | undefined): string =>
  unit === undefined ? formatAmount(amount) : `${formatAmount(amount)} ${unit}`;

const columnsIn = (currency: string | undefined): DataTableColumn<ClosedPosition>[] => [
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => position.side },
  { header: 'Aperta il', cell: (position) => formatInstant(position.opened_at) },
  { header: 'Apertura', cell: (position) => formatAmount(position.open_price) },
  { header: 'Chiusa il', cell: (position) => formatInstant(position.closed_at) },
  { header: 'Chiusura', cell: (position) => formatAmount(position.close_price) },
  { header: 'PnL', cell: (position) => <PnlAmount amount={position.pnl} unit={currency} /> },
  { header: 'PnL %', cell: (position) => <PnlPercent percent={position.pnl_percent_of_margin} /> },
  { header: 'Commissioni', cell: (position) => inUnit(position.fees, currency) },
  { header: 'Motivo', cell: (position) => position.reason },
];

/**
 * The closed positions of the flow from the most recent close, in the pages of the API (R2.2.5). The currency comes
 * from the state of the flow, read from the exchange: without it the amounts still show, the history does not depend
 * on the exchange (ADR 0143).
 */
export const ClosedPositions = ({ flowId, page }: { flowId: string; page: number }) => {
  const positions = useClosedPositions(flowId, page);
  const currency = useFlowState(flowId).data?.currency;
  if (positions.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (positions.data === undefined) {
    return <ErrorMessage error={positions.error} />;
  }
  return (
    <>
      <DataTable
        label="Posizioni chiuse"
        columns={columnsIn(currency)}
        rows={positions.data.positions}
        rowKey={(position) => `${position.closed_at}-${position.asset}`}
        empty="Nessuna posizione chiusa."
      />
      <Pagination
        page={positions.data.page}
        hasNext={positions.data.has_next}
        hrefOf={(target) => paths.flowClosedPositions.getHref(flowId, target)}
      />
    </>
  );
};
