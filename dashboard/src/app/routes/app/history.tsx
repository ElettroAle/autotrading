import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { HistoryView } from '@/features/history/components/history-view';

export const HistoryRoute = () => (
  <DashboardLayout title="Storico">
    <HistoryView />
  </DashboardLayout>
);
