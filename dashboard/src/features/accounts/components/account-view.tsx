import type { ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { NetworkBadge } from '@/components/ui/network-notice';

import { useAccounts } from '../api/get-accounts';

import { ReconciliationState } from './reconciliation-state';

type AccountViewProps = {
  readonly accountId: string;
  /** What follows the head of the account once read: its tabs and the tab chosen. */
  readonly children: ReactNode;
};

/**
 * The head of the page of the account, its network and the state of its reconciliation with an icon and a text, then
 * its tabs, once the account is read (ADR elenco-dei-conti-e-pagina-del-conto).
 */
export const AccountView = ({ accountId, children }: AccountViewProps) => {
  const accounts = useAccounts();
  if (accounts.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the account already read on the page: the warning is the page's (ADR 0119).
  if (accounts.data === undefined) {
    return <ErrorMessage error={accounts.error} />;
  }
  const account = accounts.data.find((candidate) => candidate.id === accountId);
  if (account === undefined) {
    return <p>Conto non trovato.</p>;
  }
  return (
    <>
      <section
        aria-label={account.name}
        className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded border border-slate-200 bg-white p-4"
      >
        <NetworkBadge network={account.network} networkName={account.network_name} />
        <ReconciliationState account={account} />
      </section>
      {children}
    </>
  );
};
