import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useAccounts } from '../api/get-accounts';

import { AccountItem } from './account-item';
import { ExpiringCredentialsNotice } from './credentials-expiry';

/**
 * Every account of the tenant in a compact element of its own, one column on a phone and two from a wide screen (Bug
 * 565, ADR conti-a-riquadri, ADR elenco-dei-conti-e-pagina-del-conto); what comes from the exchange may fail alone (ADR
 * 0126). At the head, the accounts whose credentials expire (ADR scadenza-nelle-pagine-chiavi-e-conti).
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
    <>
      <ExpiringCredentialsNotice accounts={accounts.data} />
      <section aria-label="Conti" className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        {accounts.data.map((account) => (
          <AccountItem key={account.id} account={account} />
        ))}
      </section>
    </>
  );
};
