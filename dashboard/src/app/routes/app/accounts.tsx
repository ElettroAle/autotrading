import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { AccountsList } from '@/features/accounts/components/accounts-list';
import { RegisterAccountForm } from '@/features/accounts/components/register-account-form';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';

// Every account with its commands, the emergency closing of its flows among them (R3.2.3).
export const AccountsRoute = () => (
  <DashboardLayout title="I tuoi conti">
    <div className="space-y-4">
      <AccountsList
        renderCommands={(account) => (
          <EmergencyClosingCommand
            scope={{ kind: 'account', accountId: account.id, accountName: account.name }}
          />
        )}
      />
      <RegisterAccountForm />
    </div>
  </DashboardLayout>
);
