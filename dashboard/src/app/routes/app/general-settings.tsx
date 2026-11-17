import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';

// The settings of the platform, not of the user: the emergency closing of every flow stays out of the page of every
// day, alone at the bottom, as in GitHub or Azure DevOps (R3.2.3, ADR voce-generale-con-la-zona-pericolosa).
export const GeneralSettingsRoute = () => (
  <DashboardLayout title="Generale">
    <DangerZone>
      <EmergencyClosingCommand scope={{ kind: 'all' }} />
    </DangerZone>
  </DashboardLayout>
);
