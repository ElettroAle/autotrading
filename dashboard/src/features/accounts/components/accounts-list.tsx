import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { NetworkBadge } from '@/components/ui/network-notice';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { formatAmount } from '@/utils/format-amount';

import { useAccountBalance } from '../api/get-account-state';
import { useAccounts, type Account } from '../api/get-accounts';
import { useFreeCapital } from '../api/get-free-capital';

import { AccountActions } from './account-actions';
import { ExchangeAmount } from './exchange-amount';
import { PublicFields } from './public-fields';

const Balance = ({ account }: { account: Account }) => (
  <ExchangeAmount reading={useAccountBalance(account.id)} unavailable="Saldo non disponibile" />
);

const FreeCapital = ({ account }: { account: Account }) => (
  <ExchangeAmount
    reading={useFreeCapital(account.id)}
    unavailable="Capitale libero non disponibile"
  />
);

const AccountOnExchange = ({ account }: { account: Account }) => {
  const exchanges = useSupportedExchanges();
  const fields =
    exchanges.data?.find((exchange) => exchange.name === account.exchange)?.fields ?? [];
  return <PublicFields fields={fields} values={account.public_fields} />;
};

const COLUMNS: DataTableColumn<Account>[] = [
  { header: 'Nome', cell: (account) => account.name },
  { header: "Conto sull'exchange", cell: (account) => <AccountOnExchange account={account} /> },
  {
    header: 'Rete',
    cell: (account) => (
      <NetworkBadge network={account.network} networkName={account.network_name} />
    ),
  },
  { header: 'Saldo', cell: (account) => <Balance account={account} /> },
  {
    header: 'Capitale allocato',
    cell: (account) => `${formatAmount(account.allocated_capital)} ${account.currency}`,
  },
  { header: 'Capitale libero', cell: (account) => <FreeCapital account={account} /> },
  { header: 'Comandi', cell: (account) => <AccountActions account={account} /> },
];

/** Every account of the tenant with what the API says of it; what comes from the exchange may fail alone (ADR 0126). */
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
    <DataTable
      label="Conti"
      columns={COLUMNS}
      rows={accounts.data}
      rowKey={(account) => account.id}
    />
  );
};
