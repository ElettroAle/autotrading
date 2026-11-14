import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { FlowVersions } from '@/features/flow-versions/components/flow-versions';

export const FlowVersionsRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <PageLayout title="Versioni della configurazione">
      <FlowVersions flowId={flowId} />
    </PageLayout>
  );
};
