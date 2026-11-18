import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { AlertDetailView } from '@/features/alerts/components/alert-detail';
import { AlertsList } from '@/features/alerts/components/alerts-list';

export const AlertsRoute = () => (
  <DashboardLayout title="Avvisi">
    <AlertsList />
  </DashboardLayout>
);

export const AlertRoute = () => {
  const { alertId = '' } = useParams();
  return (
    <DashboardLayout title="Avviso">
      <AlertDetailView alertId={alertId} />
    </DashboardLayout>
  );
};
