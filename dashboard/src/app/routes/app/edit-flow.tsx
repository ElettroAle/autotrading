import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { EditFlow } from '@/features/flow-editor/components/edit-flow';

export const EditFlowRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <PageLayout title="Configurazione del flusso">
      <EditFlow flowId={flowId} />
    </PageLayout>
  );
};
