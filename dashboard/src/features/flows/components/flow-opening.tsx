import { useAccounts } from '../api/get-accounts';
import { DRAFT_STATUS, useFlows } from '../api/get-flows';

import { DraftAssignmentForm } from './draft-assignment-form';
import { FlowResults } from './flow-results';

/**
 * What opens the overview of the flow: how it is doing in the period (R6.4.2); a draft has no account and no results
 * yet, so it opens with what it lacks to start (ADR 0125).
 */
export const FlowOpening = ({ flowId }: { flowId: string }) => {
  const flow = useFlows().data?.find((candidate) => candidate.id === flowId);
  const accounts = useAccounts();
  if (flow === undefined) {
    return null;
  }
  if (flow.status === DRAFT_STATUS) {
    return <DraftAssignmentForm flowId={flow.id} accounts={accounts.data ?? []} />;
  }
  return <FlowResults flowId={flow.id} />;
};
