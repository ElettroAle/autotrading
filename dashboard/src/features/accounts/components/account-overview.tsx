import { Card } from '@/components/ui/card';
import { DETAILS_GRID } from '@/components/ui/details-list';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';

import type { Account } from '../api/get-accounts';
import { useAccount } from '../hooks/use-account';

import { AccountBalance, AccountFreeCapital } from './account-amounts';
import { CredentialsExpiry } from './credentials-expiry';
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
 * the flows plus the free capital, then the expiry of its credentials (Bug 601, R6.2.2, ADR
 * scomposizione-del-saldo-nel-riquadro-del-conto, ADR elenco-dei-conti-e-pagina-del-conto, ADR
 * scadenza-nelle-pagine-chiavi-e-conti). The page has read the account before its tabs show.
 */
export const AccountOverview = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  if (account === undefined) {
    return null;
  }
  return (
    <Card as="section" aria-label={`Panoramica del conto ${account.name}`} className="min-w-0">
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
        <Detail term="Scadenza delle credenziali">
          <CredentialsExpiry account={account} />
        </Detail>
      </dl>
    </Card>
  );
};
