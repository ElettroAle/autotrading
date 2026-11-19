import { useId } from 'react';
import { Link } from 'react-router';

import { DETAILS_GRID } from '@/components/ui/details-list';
import { NetworkBadge } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';

import type { Account } from '../api/get-accounts';

import { AccountActions } from './account-actions';
import { AccountBalance, AccountFreeCapital } from './account-amounts';
import { CredentialsExpiryStatus } from './credentials-expiry';
import { Detail } from './detail';
import { ReconciliationState } from './reconciliation-state';

/**
 * An account in the list, compact as a resource in the list of a cloud portal: its name, network and state of the
 * reconciliation, the expiry of its credentials, its balance and free capital, and the menu of its actions. Touching it
 * opens its page, where the rest of the account is (Bug 616, ADR elenco-dei-conti-e-pagina-del-conto, ADR
 * scadenza-nelle-pagine-chiavi-e-conti).
 */
export const AccountItem = ({ account }: { readonly account: Account }) => {
  const titleId = useId();
  return (
    <article
      aria-labelledby={titleId}
      className="relative min-w-0 rounded border border-slate-200 bg-white p-4 hover:border-blue-300"
    >
      {/* Room on the right of the head for the menu «Azioni» in the corner. */}
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 pr-28">
        <h2 id={titleId} className="min-w-0 text-lg font-semibold wrap-anywhere">
          {/* The link covers the whole element: the account opens wherever it is touched. */}
          <Link
            to={paths.account.getHref(account.id)}
            className="text-blue-800 after:absolute after:inset-0 hover:underline"
          >
            {account.name}
          </Link>
        </h2>
        <NetworkBadge network={account.network} networkName={account.network_name} />
      </header>
      <div className="mt-1 flex flex-col gap-1">
        <ReconciliationState account={account} />
        <CredentialsExpiryStatus account={account} />
      </div>
      <dl className={`${DETAILS_GRID} mt-2`}>
        <Detail term="Saldo (con risultato aperto)">
          <AccountBalance account={account} />
        </Detail>
        <Detail term="Capitale libero">
          <AccountFreeCapital account={account} />
        </Detail>
      </dl>
      <AccountActions account={account} />
    </article>
  );
};
