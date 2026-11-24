import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { AccountsList } from '@/features/accounts/components/accounts-list';
import { RegisterAccountForm } from '@/features/accounts/components/register-account-form';

// Every account with its commands, then the form of registration; the emergency closing of an account is on its own
// page (ADR zona-di-emergenza-nella-pagina-del-conto).
export const AccountsRoute = () => (
  <DashboardLayout title="I tuoi conti">
    <div className="space-y-4">
      <AccountsList />
      <RegisterAccountForm />
    </div>
  </DashboardLayout>
);
