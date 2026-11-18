import { useId } from 'react';

import { DETAILS_GRID } from '@/components/ui/details-list';
import { NetworkBadge } from '@/components/ui/network-notice';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { formatAmount } from '@/utils/format-amount';

import { useAccountBalance } from '../api/get-account-state';
import type { Account } from '../api/get-accounts';
import { useFreeCapital } from '../api/get-free-capital';

import { AccountActions } from './account-actions';
import { Detail } from './detail';
import { ExchangeAmount } from './exchange-amount';
import { PublicFields } from './public-fields';
import { ReconciliationState } from './reconciliation-state';
import { ReconciliationStatus } from './reconciliation-status';
import { UnattributableMovements } from './unattributable-movements';

const Balance = ({ account }: { readonly account: Account }) => (
  <ExchangeAmount reading={useAccountBalance(account.id)} unavailable="Saldo non disponibile" />
);

const FreeCapital = ({ account }: { readonly account: Account }) => (
  <ExchangeAmount
    reading={useFreeCapital(account.id)}
    unavailable="Capitale libero non disponibile"
  />
);

const AccountOnExchange = ({ account }: { readonly account: Account }) => {
  const exchanges = useSupportedExchanges();
  const fields =
    exchanges.data?.find((exchange) => exchange.name === account.exchange)?.fields ?? [];
  return <PublicFields fields={fields} values={account.public_fields} />;
};

const hasPublicFields = (account: Account): boolean =>
  Object.keys(account.public_fields).length > 0;

/**
 * An account in a box of its own: its name, network and state of the reconciliation at the top, its data, the section
 * of the reconciliation, the movements no flow explains, then the commands on the account (Bug 565, ADR conti-a-riquadri,
 * ADR movimenti-non-spiegati-nel-riquadro-del-conto).
 */
export const AccountCard = ({ account }: { readonly account: Account }) => {
  const titleId = useId();
  return (
    <article
      aria-labelledby={titleId}
      className="min-w-0 space-y-4 rounded border border-slate-200 bg-white p-4"
    >
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 id={titleId} className="min-w-0 text-xl font-semibold wrap-anywhere">
          {account.name}
        </h2>
        <NetworkBadge network={account.network} networkName={account.network_name} />
        <ReconciliationState account={account} />
      </header>
      <dl className={DETAILS_GRID}>
        {hasPublicFields(account) && (
          <Detail term="Conto sull'exchange">
            <AccountOnExchange account={account} />
          </Detail>
        )}
        <Detail term="Saldo">
          <Balance account={account} />
        </Detail>
        <Detail term="Capitale allocato">
          {`${formatAmount(account.allocated_capital)} ${account.currency}`}
        </Detail>
        <Detail term="Capitale libero">
          <FreeCapital account={account} />
        </Detail>
      </dl>
      <ReconciliationStatus account={account} />
      <UnattributableMovements account={account} />
      <AccountActions account={account} />
    </article>
  );
};
