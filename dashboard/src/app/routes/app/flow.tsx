import { useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowCommands } from '@/features/flow-commands/components/flow-commands';
import { FlowStatistics } from '@/features/flow-statistics/components/flow-statistics';
import { EquityCurve } from '@/features/flows/components/equity-curve';
import { FlowView } from '@/features/flows/components/flow-view';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

export const FlowRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId);
  return (
    <DashboardLayout title={title}>
      <FlowView
        flowId={flowId}
        renderCommands={(flow, realMoney) => (
          <FlowCommands flowId={flow.id} status={flow.status} realMoney={realMoney} />
        )}
      />
      <PeriodSelector />
      <EquityCurve flowId={flowId} />
      <FlowStatistics flowId={flowId} />
    </DashboardLayout>
  );
};
