import { Outlet, useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { paths } from '@/config/paths';
import { AccountTabs } from '@/features/accounts/components/account-tabs';
import { AccountView } from '@/features/accounts/components/account-view';
import { useAccount } from '@/features/accounts/hooks/use-account';

// The page of the account, titled with its name: its head, its tabs and the tab chosen, as the page of a flow; «Indietro»
// leads back to the accounts when the dashboard was opened on it (ADR elenco-dei-conti-e-pagina-del-conto).
export const AccountRoute = () => {
  const { accountId = '' } = useParams();
  const title = useAccount(accountId)?.name ?? 'Conto';
  return (
    <DashboardLayout title={title} backTo={paths.accounts.getHref()}>
      <AccountView accountId={accountId}>
        <AccountTabs accountId={accountId} />
        <Outlet />
      </AccountView>
    </DashboardLayout>
  );
};
