import { DETAILS_GRID } from '@/components/ui/details-list';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';

import type { Account } from '../api/get-accounts';
import { useAccount } from '../hooks/use-account';

import { AccountBalance, AccountFreeCapital } from './account-amounts';
import { Detail } from './detail';
import { FlowsValue } from './flows-value';
import { PublicFields } from './public-fields';

const AccountOnExchange = ({ account }: { readonly account: Account }) => {
  const exchanges = useSupportedExchanges();
  const fields =
    exchanges.data?.find((exchange) => exchange.name === account.exchange)?.fields ?? [];
  return <PublicFields fields={fields} values={account.public_fields} />;
};

const hasPublicFields = (account: Account): boolean =>
  Object.keys(account.public_fields).length > 0;

/**
 * The tab Panoramica of the page of the account: where it is on the exchange, then its balance read as the value of
 * the flows plus the free capital (Bug 601, ADR scomposizione-del-saldo-nel-riquadro-del-conto, ADR
 * elenco-dei-conti-e-pagina-del-conto). The page has read the account before its tabs show.
 */
export const AccountOverview = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  if (account === undefined) {
    return null;
  }
  return (
    <section
      aria-label={`Panoramica del conto ${account.name}`}
      className="min-w-0 rounded border border-slate-200 bg-white p-4"
    >
      <dl className={DETAILS_GRID}>
        {hasPublicFields(account) && (
          <Detail term="Conto sull'exchange">
            <AccountOnExchange account={account} />
          </Detail>
        )}
        <Detail term="Saldo (con risultato aperto)">
          <AccountBalance account={account} />
        </Detail>
        <Detail term="Valore dei flussi">
          <FlowsValue account={account} />
        </Detail>
        <Detail term="Capitale libero">
          <AccountFreeCapital account={account} />
        </Detail>
      </dl>
    </section>
  );
};
