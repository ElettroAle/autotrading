import { Outlet, useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { paths } from '@/config/paths';
import { AccountTabs } from '@/features/accounts/components/account-tabs';
import { AccountView } from '@/features/accounts/components/account-view';
import { useAccount } from '@/features/accounts/hooks/use-account';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';

// The emergency closing of the flows of the account, from the same reading of the accounts as the page; none while the
// account is not read or not found (ADR zona-di-emergenza-nella-pagina-del-conto).
const AccountEmergencyZone = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  if (account === undefined) {
    return null;
  }
  return (
    <DangerZone>
      <EmergencyClosingCommand
        scope={{ kind: 'account', accountId: account.id, accountName: account.name }}
      />
    </DangerZone>
  );
};

// The page of the account, titled with its name: its head, its tabs and the tab chosen, as the page of a flow, then the
// emergency closing alone at the bottom whichever tab is open; «Indietro» leads back to the accounts when the dashboard
// was opened on it (ADR elenco-dei-conti-e-pagina-del-conto, ADR zona-di-emergenza-nella-pagina-del-conto).
export const AccountRoute = () => {
  const { accountId = '' } = useParams();
  const title = useAccount(accountId)?.name ?? 'Conto';
  return (
    <DashboardLayout title={title} backTo={paths.accounts.getHref()}>
      <AccountView accountId={accountId}>
        <AccountTabs accountId={accountId} />
        <Outlet />
      </AccountView>
      <AccountEmergencyZone accountId={accountId} />
    </DashboardLayout>
  );
};
