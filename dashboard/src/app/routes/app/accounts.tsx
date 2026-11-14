import { PageLayout } from '@/components/layouts/page-layout';
import { AccountsList } from '@/features/accounts/components/accounts-list';
import { RegisterAccountForm } from '@/features/accounts/components/register-account-form';

export const AccountsRoute = () => (
  <PageLayout title="I tuoi conti">
    <div className="space-y-4">
      <AccountsList />
      <RegisterAccountForm />
    </div>
  </PageLayout>
);
