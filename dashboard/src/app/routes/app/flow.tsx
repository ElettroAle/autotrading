import { Outlet, useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowCommands } from '@/features/flow-commands/components/flow-commands';
import { OpeningsSuspension } from '@/features/flow-commands/components/openings-suspension';
import { FlowTabs } from '@/features/flows/components/flow-tabs';
import { FlowView } from '@/features/flows/components/flow-view';
import { IntervalLabel } from '@/features/flows/components/interval-label';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

// The page of the flow: its name, its status, the suspension of its openings whatever the cause (R3.2.2, R3.3.2) and
// the commands, the period, the tabs and the tab chosen, in this order; the period sits above the tabs and holds for
// all of them (R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune).
export const FlowRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId);
  return (
    <DashboardLayout title={title}>
      <FlowView
        flowId={flowId}
        renderCommands={(flow, realMoney) => (
          <>
            <OpeningsSuspension flowId={flow.id} />
            <FlowCommands flowId={flow.id} status={flow.status} realMoney={realMoney} />
          </>
        )}
      >
        <PeriodSelector />
        <IntervalLabel />
        <FlowTabs flowId={flowId} />
        <Outlet />
      </FlowView>
    </DashboardLayout>
  );
};
