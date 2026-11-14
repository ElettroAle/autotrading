import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { AccountsList } from '@/features/accounts/components/accounts-list';
import { RegisterAccountForm } from '@/features/accounts/components/register-account-form';

export const AccountsRoute = () => (
  <DashboardLayout title="I tuoi conti">
    <div className="space-y-4">
      <AccountsList />
      <RegisterAccountForm />
    </div>
  </DashboardLayout>
);
