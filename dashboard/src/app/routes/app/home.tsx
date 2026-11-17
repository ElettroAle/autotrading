import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';
import { FlowViewTabs } from '@/features/flows/components/flow-view-tabs';
import { FlowsList } from '@/features/flows/components/flows-list';
import { FlowsToolbar } from '@/features/flows/components/flows-toolbar';

// The list of the flows, with the emergency closing of every flow of the user alone at the bottom of the page (R3.2.3,
// ADR zona-di-emergenza-in-fondo-alla-pagina).
export const HomeRoute = () => (
  <DashboardLayout title="I tuoi flussi">
    <FlowViewTabs />
    <FlowsToolbar />
    <FlowsList />
    <DangerZone>
      <EmergencyClosingCommand scope={{ kind: 'all' }} />
    </DangerZone>
  </DashboardLayout>
);
