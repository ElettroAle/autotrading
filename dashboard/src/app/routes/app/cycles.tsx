import { useParams, useSearchParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { CyclesList } from '@/features/cycles/components/cycles-list';
import { pageOf } from '@/utils/page-number';

export const CyclesRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <DashboardLayout title="Cicli del flusso">
      <CyclesList flowId={flowId} page={pageOf(search.get('page'))} />
    </DashboardLayout>
  );
};
