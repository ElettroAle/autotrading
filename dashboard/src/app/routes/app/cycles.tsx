import { useParams, useSearchParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { CyclesList } from '@/features/cycles/components/cycles-list';
import { pageOf } from '@/utils/page-number';

export const CyclesRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <PageLayout title="Cicli del flusso">
      <CyclesList flowId={flowId} page={pageOf(search.get('page'))} />
    </PageLayout>
  );
};
