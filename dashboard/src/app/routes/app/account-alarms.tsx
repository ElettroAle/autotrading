import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { ReconciliationAlarms } from '@/features/accounts/components/reconciliation-alarms';
import { useAccountTitle } from '@/features/accounts/hooks/use-account-title';

export const AccountAlarmsRoute = () => {
  const { accountId = '' } = useParams();
  const title = useAccountTitle(accountId, 'Allarmi');
  return (
    <DashboardLayout title={title}>
      <ReconciliationAlarms accountId={accountId} />
    </DashboardLayout>
  );
};
