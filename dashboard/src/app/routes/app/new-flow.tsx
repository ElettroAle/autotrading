import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { CreateFlow } from '@/features/flow-editor/components/create-flow';

export const NewFlowRoute = () => (
  <DashboardLayout title="Nuovo flusso">
    <CreateFlow />
  </DashboardLayout>
);
