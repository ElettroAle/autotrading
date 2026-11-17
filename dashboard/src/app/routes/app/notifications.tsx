import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { NotificationsView } from '@/features/notifications/components/notifications-view';

export const NotificationsRoute = () => (
  <DashboardLayout title="Notifiche">
    <NotificationsView />
  </DashboardLayout>
);
