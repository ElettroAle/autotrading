import { useParams, useSearchParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { CyclesList } from '@/features/cycles/components/cycles-list';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';
import { pageOf } from '@/utils/page-number';

export const CyclesRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Cicli');
  const [search] = useSearchParams();
  return (
    <DashboardLayout title={title}>
      <CyclesList
        flowId={flowId}
        page={pageOf(search.get('page'))}
        outcome={search.get('outcome') ?? ''}
      />
    </DashboardLayout>
  );
};
