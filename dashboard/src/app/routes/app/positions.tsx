import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { OpenPositions } from '@/features/flow-positions/components/open-positions';

export const PositionsRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <DashboardLayout title="Posizioni aperte del flusso">
      <OpenPositions flowId={flowId} />
    </DashboardLayout>
  );
};
