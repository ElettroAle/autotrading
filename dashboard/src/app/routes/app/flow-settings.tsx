import { Navigate, useLocation, useParams } from 'react-router';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { DangerZone } from '@/components/ui/danger-zone';
import { paths } from '@/config/paths';
import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';
import { ArchiveFlowCommand } from '@/features/flow-commands/components/archive-flow-command';
import { FlowVersions } from '@/features/flow-versions/components/flow-versions';
import { DRAFT_STATUS, useFlows } from '@/features/flows/api/get-flows';
import { FlowConfiguration } from '@/features/flows/components/flow-configuration';
import { useFlowTitle } from '@/features/flows/hooks/use-flow-title';

// The commands of danger of a flow found, from the same reading of the flows as the page: the emergency closing for a
// flow that may hold positions, not a draft, and Archivia for a stopped flow or a draft (ADR
// impostazioni-del-flusso-dall-ingranaggio).
const FlowDangerZone = ({ flowId }: { readonly flowId: string }) => {
  const flow = useFlows().data?.find((candidate) => candidate.id === flowId);
  if (flow === undefined) {
    return null;
  }
  return (
    <DangerZone title="Zona pericolosa">
      {flow.status === DRAFT_STATUS ? null : (
        <EmergencyClosingCommand scope={{ kind: 'flow', flowId: flow.id, flowName: flow.name }} />
      )}
      <ArchiveFlowCommand flowId={flow.id} status={flow.status} />
    </DangerZone>
  );
};

// The settings of the flow, behind the gear of its page and out of its tabs, so reading and writing do not mix: the
// configuration with its commands, its versions and, at the bottom, the zone of danger (Bug 560, ADR
// impostazioni-del-flusso-dall-ingranaggio).
export const FlowSettingsRoute = () => {
  const { flowId = '' } = useParams();
  const title = useFlowTitle(flowId, 'Impostazioni');
  return (
    <DashboardLayout title={title}>
      <FlowConfiguration flowId={flowId} />
      <FlowVersions flowId={flowId} />
      <FlowDangerZone flowId={flowId} />
    </DashboardLayout>
  );
};

/** The old address of the configuration of a flow leads to its settings, with its query. */
export const OldFlowVersionsRoute = () => {
  const { flowId = '' } = useParams();
  const { search } = useLocation();
  return <Navigate to={`${paths.flowSettings.getHref(flowId)}${search}`} replace />;
};
