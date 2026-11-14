import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { CycleView } from '@/features/cycles/components/cycle-view';

export const CycleRoute = () => {
  const { flowId = '', plannedAt = '' } = useParams();
  return (
    <DashboardLayout title="Dettaglio del ciclo">
      <CycleView flowId={flowId} plannedAt={plannedAt} />
    </DashboardLayout>
  );
};
