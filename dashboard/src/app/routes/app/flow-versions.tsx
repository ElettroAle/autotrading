import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { FlowVersions } from '@/features/flow-versions/components/flow-versions';
import { FlowConfiguration } from '@/features/flows/components/flow-configuration';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

// What does not depend on the period, out of the tabs and without the period: configuration, its commands and its
// versions (R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune).
export const FlowVersionsRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Configurazione');
  return (
    <DashboardLayout title={title}>
      <FlowConfiguration flowId={flowId} />
      <FlowVersions flowId={flowId} />
    </DashboardLayout>
  );
};
