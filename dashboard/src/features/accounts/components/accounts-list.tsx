import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useAccounts } from '../api/get-accounts';

import { AccountCard } from './account-card';

/**
 * Every account of the tenant in a box of its own, one column on a phone and two from a wide screen (Bug 565, ADR
 * conti-a-riquadri); what comes from the exchange may fail alone (ADR 0126).
 */
export const AccountsList = () => {
  const accounts = useAccounts();
  if (accounts.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (accounts.data === undefined) {
    return <ErrorMessage error={accounts.error} />;
  }
  if (accounts.data.length === 0) {
    return <p className="text-slate-600">Nessun conto registrato.</p>;
  }
  return (
    <section aria-label="Conti" className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
      {accounts.data.map((account) => (
        <AccountCard key={account.id} account={account} />
      ))}
    </section>
  );
};
