import { useParams, useSearchParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { useAccounts } from '@/features/accounts/api/get-accounts';
import { AccountCapitalChanges } from '@/features/capital-changes/components/account-capital-changes';
import { pageOf } from '@/utils/page-number';

const titleOf = (name: string | undefined): string =>
  name === undefined ? 'Storico del capitale' : `Storico del capitale di ${name}`;

/** The history of the capital of an account, under the period it is filtered by (R3.4.2). */
export const AccountCapitalRoute = () => {
  const { accountId = '' } = useParams();
  const [search] = useSearchParams();
  const name = useAccounts().data?.find((account) => account.id === accountId)?.name;
  return (
    <DashboardLayout title={titleOf(name)}>
      <div className="space-y-4">
        <PeriodSelector />
        <AccountCapitalChanges accountId={accountId} page={pageOf(search.get('page'))} />
      </div>
    </DashboardLayout>
  );
};
