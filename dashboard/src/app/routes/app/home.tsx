import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { FlowViewTabs } from '@/features/flows/components/flow-view-tabs';
import { FlowsList } from '@/features/flows/components/flows-list';
import { FlowsToolbar } from '@/features/flows/components/flows-toolbar';

export const HomeRoute = () => (
  <DashboardLayout title="I tuoi flussi">
    <FlowViewTabs />
    <FlowsToolbar />
    <FlowsList />
  </DashboardLayout>
);
