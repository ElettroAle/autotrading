import { useParams, useSearchParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { ClosedPositions } from '@/features/flow-positions/components/closed-positions';
import { pageOf } from '@/utils/page-number';

export const ClosedPositionsRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <DashboardLayout title="Posizioni chiuse del flusso">
      <ClosedPositions flowId={flowId} page={pageOf(search.get('page'))} />
    </DashboardLayout>
  );
};
