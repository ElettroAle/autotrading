import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { FlowVersions } from '@/features/flow-versions/components/flow-versions';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

export const FlowVersionsRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Versioni della configurazione');
  return (
    <DashboardLayout title={title}>
      <FlowVersions flowId={flowId} />
    </DashboardLayout>
  );
};
