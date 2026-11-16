import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { EditFlow } from '@/features/flow-editor/components/edit-flow';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

export const EditFlowRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Modifica della configurazione');
  return (
    <DashboardLayout title={title}>
      <EditFlow flowId={flowId} />
    </DashboardLayout>
  );
};
