import { Icon } from '@/components/ui/icons/icon';

import { useAccountReconciliation } from '../api/get-account-reconciliation';
import type { Account } from '../api/get-accounts';

/**
 * Whether the balance of the account is the expected one, as the API says it, with an icon and a text, never the
 * colour alone; while it is not read, or cannot be, the section of the reconciliation says so (ADR conti-a-riquadri).
 */
export const ReconciliationState = ({ account }: { readonly account: Account }) => {
  const reconciliation = useAccountReconciliation(account.id);
  if (reconciliation.data === undefined) {
    return null;
  }
  const { aligned } = reconciliation.data;
  return (
    <p
      role="status"
      aria-label="Stato della riconciliazione"
      className={`flex items-center gap-2 font-semibold ${aligned ? 'text-green-800' : 'text-red-800'}`}
    >
      <Icon name={aligned ? 'circle-check' : 'circle-alert'} />
      {`Riconciliazione: ${aligned ? 'allineato' : 'allarme'}`}
    </p>
  );
};
