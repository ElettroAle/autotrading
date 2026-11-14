import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { formatRate, formatRoundedAmount, formatRoundedResult } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import type { HistoryPosition } from '../api/get-closed-position-history';

const resultClass = (text: string): string =>
  text.startsWith('-') ? 'text-red-700' : 'text-green-700';

const COLUMNS: DataTableColumn<HistoryPosition>[] = [
  { header: 'Chiusura', cell: (position) => formatInstant(position.closed_at) },
  { header: 'Flusso', cell: (position) => position.flow },
  { header: 'Asset', cell: (position) => position.asset },
  { header: 'Direzione', cell: (position) => `${position.side} ${position.leverage}x` },
  { header: 'Prezzo di apertura', cell: (position) => formatRoundedAmount(position.open_price) },
  { header: 'Prezzo di chiusura', cell: (position) => formatRoundedAmount(position.close_price) },
  {
    header: 'PnL',
    cell: (position) => (
      <span className={resultClass(position.pnl)}>
        {formatRoundedResult(position.pnl)} ({formatRate(position.pnl_percent_of_margin)})
      </span>
    ),
  },
  { header: 'Commissioni', cell: (position) => formatRoundedAmount(position.fees) },
  { header: 'Motivo', cell: (position) => position.reason },
];

/** The closed positions found, with their result as the API gives it. */
export const ClosedPositionHistoryTable = ({
  positions,
}: {
  positions: readonly HistoryPosition[];
}) => (
  <DataTable
    label="Posizioni chiuse"
    columns={COLUMNS}
    rows={positions}
    rowKey={(position) => position.id}
    empty="Nessuna posizione chiusa trovata."
  />
);
