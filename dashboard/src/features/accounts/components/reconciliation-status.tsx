import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import { useConfirmReconciliation } from '../api/confirm-reconciliation';
import {
  useAccountReconciliation,
  type AccountReconciliation,
} from '../api/get-account-reconciliation';
import type { Account } from '../api/get-accounts';

import { DeviationThresholdForm } from './deviation-threshold-form';

const Detail = ({ term, children }: { readonly term: string; readonly children: ReactNode }) => (
  <>
    <dt className="font-medium text-slate-600">{term}</dt>
    <dd aria-label={term} className={DETAIL_VALUE}>
      {children}
    </dd>
  </>
);

const STATE_STYLES = {
  aligned: 'rounded bg-green-100 px-2 py-0.5 font-semibold text-green-900',
  alarm: 'rounded bg-red-100 px-2 py-0.5 font-semibold text-red-900',
} as const;

const ReconciliationDetails = ({
  account,
  reconciliation,
}: {
  readonly account: Account;
  readonly reconciliation: AccountReconciliation;
}) => {
  const { aligned, last_comparison: comparison, threshold_percent: threshold } = reconciliation;
  const amount = (value: string) => `${formatAmount(value)} ${account.currency}`;
  return (
    <dl className={DETAILS_GRID}>
      <Detail term="Stato">
        <span className={aligned ? STATE_STYLES.aligned : STATE_STYLES.alarm}>
          {aligned ? 'allineato' : 'allarme'}
        </span>
      </Detail>
      {comparison === null ? (
        <Detail term="Ultimo confronto">nessun confronto ancora</Detail>
      ) : (
        <>
          <Detail term="Ultimo confronto">{formatInstant(comparison.compared_at)}</Detail>
          <Detail term="Saldo atteso">{amount(comparison.expected_balance)}</Detail>
          <Detail term="Saldo letto">{amount(comparison.read_balance)}</Detail>
          <Detail term="Scostamento">{`${formatAmount(comparison.deviation_percent)}%`}</Detail>
        </>
      )}
      <Detail term="Soglia">{`${formatAmount(threshold)}%`}</Detail>
    </dl>
  );
};

type ConfirmAlarmProps = { readonly account: Account; readonly onDone: () => void };

// The confirmation closes the alarm and lets the flows of the account open again: it is asked first (R3.3.2).
const ConfirmAlarm = ({ account, onDone }: ConfirmAlarmProps) => {
  const confirmation = useConfirmReconciliation(account.id);
  return (
    <ConfirmationDialog
      title={`Verifica del conto ${account.name}`}
      confirmLabel="Conferma la verifica"
      onConfirm={() => confirmation.mutate(undefined, { onSuccess: onDone })}
      onCancel={onDone}
      pending={confirmation.isPending}
      error={confirmation.error}
    >
      {`Confermi di aver verificato il saldo del conto ${account.name}: l'allarme si chiude e i suoi flussi tornano ad aprire posizioni.`}
    </ConfirmationDialog>
  );
};

type Action = 'none' | 'confirming' | 'threshold';

/**
 * Whether the balance of the account is the expected one, as the API says it, with the commands on it: the confirmation
 * of an open alarm, its alarms and the threshold (R3.3.2, ADR stato-della-riconciliazione-nella-dashboard).
 */
export const ReconciliationStatus = ({ account }: { readonly account: Account }) => {
  const reconciliation = useAccountReconciliation(account.id);
  const [action, setAction] = useState<Action>('none');
  if (reconciliation.isPending) {
    return <Loading />;
  }
  if (reconciliation.data === undefined) {
    return <ErrorMessage error={reconciliation.error} />;
  }
  const done = () => setAction('none');
  return (
    <section aria-label={`Riconciliazione del conto ${account.name}`} className="space-y-2">
      <ReconciliationDetails account={account} reconciliation={reconciliation.data} />
      <div className="flex flex-wrap gap-2">
        {reconciliation.data.open_alarm !== null && (
          <button
            type="button"
            onClick={() => setAction('confirming')}
            className={SECONDARY_COMMAND}
          >
            Ho verificato
          </button>
        )}
        <Link to={paths.accountAlarms.getHref(account.id)} className={SECONDARY_COMMAND}>
          Allarmi
        </Link>
        <button type="button" onClick={() => setAction('threshold')} className={SECONDARY_COMMAND}>
          Modifica la soglia
        </button>
      </div>
      {action === 'confirming' && <ConfirmAlarm account={account} onDone={done} />}
      {action === 'threshold' && (
        <DeviationThresholdForm
          account={account}
          threshold={reconciliation.data.threshold_percent}
          onSaved={done}
          onCancel={done}
        />
      )}
    </section>
  );
};
