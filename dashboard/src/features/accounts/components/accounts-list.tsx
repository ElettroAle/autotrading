import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatAmount } from '@/utils/format-amount';

import { useAccountBalance } from '../api/get-account-state';
import { useAccounts, type Account } from '../api/get-accounts';
import { useFreeCapital } from '../api/get-free-capital';

import { ExchangeAmount } from './exchange-amount';

// Until the dashboard has its own form (R2.3.1), an account is registered from the interactive page of the API.
const REGISTRATION_ON_API = '/docs#/conti/register_account_accounts_post';

const NETWORK_LABELS: Readonly<Record<string, string>> = { test: 'testnet', real: 'mainnet' };

const Balance = ({ account }: { account: Account }) => (
  <ExchangeAmount reading={useAccountBalance(account.id)} unavailable="Saldo non disponibile" />
);

const FreeCapital = ({ account }: { account: Account }) => (
  <ExchangeAmount
    reading={useFreeCapital(account.id)}
    unavailable="Capitale libero non disponibile"
  />
);

const COLUMNS: DataTableColumn<Account>[] = [
  { header: 'Nome', cell: (account) => account.name },
  { header: 'Rete', cell: (account) => NETWORK_LABELS[account.network] ?? account.network },
  { header: 'Saldo', cell: (account) => <Balance account={account} /> },
  {
    header: 'Capitale allocato',
    cell: (account) => `${formatAmount(account.allocated_capital)} ${account.currency}`,
  },
  { header: 'Capitale libero', cell: (account) => <FreeCapital account={account} /> },
];

/** Every account of the tenant with what the API says of it; what comes from the exchange may fail alone (ADR 0126). */
export const AccountsList = () => {
  const accounts = useAccounts();
  if (accounts.isPending) {
    return <Loading />;
  }
  if (accounts.isError) {
    return <ErrorMessage error={accounts.error} />;
  }
  if (accounts.data.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-slate-600">Nessun conto registrato.</p>
        <a href={REGISTRATION_ON_API} className="font-medium text-blue-800 hover:underline">
          Registra un conto
        </a>
      </div>
    );
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
