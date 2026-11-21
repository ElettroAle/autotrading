import { useFlow } from '../api/get-flow';
import { DRAFT_STATUS } from '../api/get-flows';

import { DraftReadiness } from './draft-readiness';
import { FlowResults } from './flow-results';

/**
 * What opens the overview of the flow: how it is doing in the period (R6.4.2); a draft has no results yet, so it opens
 * with what it lacks to start and the way to its configuration (ADR assegnazione-della-bozza-nel-form-di-configurazione).
 */
export const FlowOpening = ({ flowId }: { flowId: string }) => {
  const flow = useFlow(flowId).data;
  if (flow === undefined) {
    return null;
  }
  if (flow.status === DRAFT_STATUS) {
    return <DraftReadiness flow={flow} />;
  }
  return <FlowResults flowId={flow.id} />;
};
