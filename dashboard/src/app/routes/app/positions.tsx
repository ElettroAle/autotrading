import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { OpenPositions } from '@/features/flow-positions/components/open-positions';

export const PositionsRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <PageLayout title="Posizioni aperte del flusso">
      <OpenPositions flowId={flowId} />
    </PageLayout>
  );
};
