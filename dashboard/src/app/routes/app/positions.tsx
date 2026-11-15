import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { OpenPositions } from '@/features/flow-positions/components/open-positions';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

export const PositionsRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Posizioni aperte');
  return (
    <DashboardLayout title={title}>
      <OpenPositions flowId={flowId} />
    </DashboardLayout>
  );
};
