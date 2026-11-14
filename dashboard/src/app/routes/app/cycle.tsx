import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { CycleView } from '@/features/cycles/components/cycle-view';

export const CycleRoute = () => {
  const { flowId = '', plannedAt = '' } = useParams();
  return (
    <PageLayout title="Dettaglio del ciclo">
      <CycleView flowId={flowId} plannedAt={plannedAt} />
    </PageLayout>
  );
};
