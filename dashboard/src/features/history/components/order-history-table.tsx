import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { formatRoundedAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import type { HistoryExecution, HistoryOrder } from '../api/get-order-history';

const NO_FLOW = 'nessun flusso';

const executionsLabel = (count: number): string =>
  count === 1 ? '1 esecuzione' : `${count} esecuzioni`;

/** The executions of an order, open on request: the row of the order stays short (ADR 0139). */
const Executions = ({ executions }: { executions: readonly HistoryExecution[] }) => {
  if (executions.length === 0) {
    return <span className="text-slate-600">Nessuna esecuzione</span>;
  }
  return (
    <details>
      <summary className="cursor-pointer text-blue-800">
        {executionsLabel(executions.length)}
      </summary>
      <table aria-label="Esecuzioni" className="mt-2 text-xs">
        <thead className="text-left">
          <tr>
            <th scope="col" className="pr-3">
              Istante
            </th>
            <th scope="col" className="pr-3">
              Prezzo
            </th>
            <th scope="col" className="pr-3">
              Quantità
            </th>
            <th scope="col">Commissioni</th>
          </tr>
        </thead>
        <tbody>
          {executions.map((execution) => (
            <tr key={`${execution.executed_at}/${execution.price}/${execution.size}`}>
              <td className="pr-3">{formatInstant(execution.executed_at)}</td>
              <td className="pr-3">{formatRoundedAmount(execution.price)}</td>
              <td className="pr-3">{execution.size}</td>
              <td>{formatRoundedAmount(execution.fee)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
};

const COLUMNS: DataTableColumn<HistoryOrder>[] = [
  { header: 'Istante', cell: (order) => formatInstant(order.created_at) },
  { header: 'Conto', cell: (order) => order.account },
  { header: 'Flusso', cell: (order) => order.flow ?? NO_FLOW },
  { header: 'Asset', cell: (order) => order.asset },
  {
    header: 'Ordine',
    cell: (order) => `${order.closing ? 'chiusura' : 'apertura'} ${order.direction}`,
  },
  { header: 'Stato', cell: (order) => order.status },
  { header: 'Esecuzioni', cell: (order) => <Executions executions={order.executions} /> },
];

/** The orders found; each opens on its executions, with price, quantity and fee. */
export const OrderHistoryTable = ({ orders }: { orders: readonly HistoryOrder[] }) => (
  <DataTable
    label="Ordini"
    columns={COLUMNS}
    rows={orders}
    rowKey={(order) => order.id}
    empty="Nessun ordine trovato."
  />
);
