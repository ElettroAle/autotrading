import { Outlet, useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';
import { FlowCommands } from '@/features/flow-commands/components/flow-commands';
import { OpeningsSuspension } from '@/features/flow-commands/components/openings-suspension';
import { DRAFT_STATUS, useFlows } from '@/features/flows/api/get-flows';
import { FlowTabs } from '@/features/flows/components/flow-tabs';
import { FlowView } from '@/features/flows/components/flow-view';
import { IntervalLabel } from '@/features/flows/components/interval-label';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

// The emergency closing of a flow found and not a draft, which has positions to close, from the same reading of the
// flows as the page (ADR zona-di-emergenza-in-fondo-alla-pagina).
const FlowDangerZone = ({ flowId }: { readonly flowId: string }) => {
  const flow = useFlows().data?.find((candidate) => candidate.id === flowId);
  if (flow === undefined || flow.status === DRAFT_STATUS) {
    return null;
  }
  return (
    <DangerZone>
      <EmergencyClosingCommand scope={{ kind: 'flow', flowId: flow.id, flowName: flow.name }} />
    </DangerZone>
  );
};

// The page of the flow: its name, its status, the suspension of its openings whatever the cause (R3.2.2, R3.3.2) and
// the commands, the period, the tabs and the tab chosen, in this order; the period sits above the tabs and holds for
// all of them (R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune). The emergency closing of the flow
// stands alone at the bottom of the page (R3.2.3, ADR zona-di-emergenza-in-fondo-alla-pagina).
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
            <FlowCommands
              flowId={flow.id}
              flowName={flow.name}
              status={flow.status}
              realMoney={realMoney}
            />
          </>
        )}
      >
        <PeriodSelector />
        <IntervalLabel />
        <FlowTabs flowId={flowId} />
        <Outlet />
      </FlowView>
      <FlowDangerZone flowId={flowId} />
    </DashboardLayout>
  );
};
