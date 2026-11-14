import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { EditFlow } from '@/features/flow-editor/components/edit-flow';

export const EditFlowRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <DashboardLayout title="Configurazione del flusso">
      <EditFlow flowId={flowId} />
    </DashboardLayout>
  );
};
