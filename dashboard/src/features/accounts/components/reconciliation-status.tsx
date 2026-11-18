import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { DETAILS_GRID } from '@/components/ui/details-list';
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

import { Detail } from './detail';
import { DeviationThresholdForm } from './deviation-threshold-form';

const ReconciliationDetails = ({
  account,
  reconciliation,
}: {
  readonly account: Account;
  readonly reconciliation: AccountReconciliation;
}) => {
  const { last_comparison: comparison, threshold_percent: threshold } = reconciliation;
  const amount = (value: string) => `${formatAmount(value)} ${account.currency}`;
  return (
    <dl className={DETAILS_GRID}>
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

type SectionProps = { readonly account: Account; readonly children: ReactNode };

/** The section of the reconciliation in the box of the account, with its title even while it is read (ADR conti-a-riquadri). */
const ReconciliationSection = ({ account, children }: SectionProps) => (
  <section
    aria-label={`Riconciliazione del conto ${account.name}`}
    className="space-y-2 border-t border-slate-200 pt-3"
  >
    <h3 className="font-semibold">Riconciliazione</h3>
    {children}
  </section>
);

const ReconciliationContent = ({ account }: { readonly account: Account }) => {
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
    <>
      <ReconciliationDetails account={account} reconciliation={reconciliation.data} />
      <div className="flex flex-wrap gap-2">
        {reconciliation.data.open_alarm !== null && (
          <CommandButton tone="secondary" onClick={() => setAction('confirming')}>
            Ho verificato
          </CommandButton>
        )}
        <Link
          to={paths.alerts.getHref({ resource_id: account.id, state: 'all' })}
          className={SECONDARY_COMMAND}
        >
          Allarmi
        </Link>
        <CommandButton tone="secondary" onClick={() => setAction('threshold')}>
          Modifica la soglia
        </CommandButton>
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
    </>
  );
};

/**
 * The data of the reconciliation of the account, as the API says it, with the commands on it: the confirmation of an
 * open alarm, its alarms and the threshold (R3.3.2, ADR stato-della-riconciliazione-nella-dashboard); whether it is
 * aligned is said in the header of the box (ADR conti-a-riquadri).
 */
export const ReconciliationStatus = ({ account }: { readonly account: Account }) => (
  <ReconciliationSection account={account}>
    <ReconciliationContent account={account} />
  </ReconciliationSection>
);
