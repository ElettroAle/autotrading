import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { FlowView } from '@/features/flows/components/flow-view';

export const FlowRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <PageLayout title="Flusso">
      <FlowView flowId={flowId} />
    </PageLayout>
  );
};
