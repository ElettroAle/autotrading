import { useParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowStatistics } from '@/features/flow-statistics/components/flow-statistics';
import { EquityCurve } from '@/features/flows/components/equity-curve';
import { FlowView } from '@/features/flows/components/flow-view';

export const FlowRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <PageLayout title="Flusso">
      <FlowView flowId={flowId} />
      <PeriodSelector />
      <EquityCurve flowId={flowId} />
      <FlowStatistics flowId={flowId} />
    </PageLayout>
  );
};
