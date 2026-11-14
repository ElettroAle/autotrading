import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { FlowVersions } from '@/features/flow-versions/components/flow-versions';

export const FlowVersionsRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <DashboardLayout title="Versioni della configurazione">
      <FlowVersions flowId={flowId} />
    </DashboardLayout>
  );
};
