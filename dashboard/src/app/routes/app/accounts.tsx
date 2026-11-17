import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { useAccounts } from '@/features/accounts/api/get-accounts';
import { AccountsList } from '@/features/accounts/components/accounts-list';
import { RegisterAccountForm } from '@/features/accounts/components/register-account-form';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';

// The emergency closing of the flows of each account, from the same reading of the accounts as the list; without an
// account there is nothing to close (ADR zona-di-emergenza-in-fondo-alla-pagina).
const AccountsDangerZone = () => {
  const accounts = useAccounts().data ?? [];
  if (accounts.length === 0) {
    return null;
  }
  return (
    <DangerZone>
      {accounts.map((account) => (
        <EmergencyClosingCommand
          key={account.id}
          scope={{ kind: 'account', accountId: account.id, accountName: account.name }}
        />
      ))}
    </DangerZone>
  );
};

// Every account with its commands, then the form of registration, then the emergency closing alone at the bottom of
// the page (R3.2.3).
export const AccountsRoute = () => (
  <DashboardLayout title="I tuoi conti">
    <div className="space-y-4">
      <AccountsList />
      <RegisterAccountForm />
    </div>
    <AccountsDangerZone />
  </DashboardLayout>
);
