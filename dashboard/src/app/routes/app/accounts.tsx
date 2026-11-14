import { PageLayout } from '@/components/layouts/page-layout';
import { AccountsList } from '@/features/accounts/components/accounts-list';

export const AccountsRoute = () => (
  <PageLayout title="I tuoi conti">
    <AccountsList />
  </PageLayout>
);
