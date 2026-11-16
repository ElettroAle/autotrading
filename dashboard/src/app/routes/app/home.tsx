import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';
import { FlowViewTabs } from '@/features/flows/components/flow-view-tabs';
import { FlowsList } from '@/features/flows/components/flows-list';
import { FlowsToolbar } from '@/features/flows/components/flows-toolbar';

// The list of the flows, with the emergency closing of every flow of the user (R3.2.3).
export const HomeRoute = () => (
  <DashboardLayout title="I tuoi flussi">
    <FlowViewTabs />
    <FlowsToolbar />
    <div className="mb-4">
      <EmergencyClosingCommand scope={{ kind: 'all' }} />
    </div>
    <FlowsList />
  </DashboardLayout>
);
