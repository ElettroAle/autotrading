import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { FlowViewTabs } from '@/features/flows/components/flow-view-tabs';
import { FlowsList } from '@/features/flows/components/flows-list';
import { FlowsToolbar } from '@/features/flows/components/flows-toolbar';

// The list of the flows, the page of every day: the emergency closing of every flow lives in «Generale» of the settings
// (ADR voce-generale-con-la-zona-pericolosa).
export const HomeRoute = () => (
  <DashboardLayout title="I tuoi flussi">
    <FlowViewTabs />
    <FlowsToolbar />
    <FlowsList />
  </DashboardLayout>
);
