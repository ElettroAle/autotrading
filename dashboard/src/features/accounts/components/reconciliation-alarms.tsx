import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import type { ReconciliationAlarm } from '../api/get-account-reconciliation';
import { useReconciliationAlarms } from '../api/get-reconciliation-alarms';

// An alarm stays open until the user confirms it (R3.3.1).
const COLUMNS: DataTableColumn<ReconciliationAlarm>[] = [
  { header: 'Aperto il', cell: (alarm) => formatInstant(alarm.opened_at) },
  { header: 'Stato', cell: (alarm) => (alarm.confirmed_at === null ? 'aperto' : 'chiuso') },
  {
    header: 'Confermato il',
    cell: (alarm) => (alarm.confirmed_at === null ? '—' : formatInstant(alarm.confirmed_at)),
  },
  { header: 'Saldo atteso', cell: (alarm) => formatAmount(alarm.expected_balance) },
  { header: 'Saldo letto', cell: (alarm) => formatAmount(alarm.read_balance) },
  { header: 'Scostamento', cell: (alarm) => `${formatAmount(alarm.deviation_percent)}%` },
];

/** The alarms of reconciliation of the account, open and closed, the most recent first as the API lists them (R3.3.2). */
export const ReconciliationAlarms = ({ accountId }: { readonly accountId: string }) => {
  const alarms = useReconciliationAlarms(accountId);
  if (alarms.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the alarms already read on the page: the warning is the page's (ADR 0119).
  if (alarms.data === undefined) {
    return <ErrorMessage error={alarms.error} />;
  }
  return (
    <DataTable
      label="Allarmi di riconciliazione"
      columns={COLUMNS}
      rows={alarms.data}
      rowKey={(alarm) => alarm.opened_at}
      empty="Nessun allarme di riconciliazione."
    />
  );
};
