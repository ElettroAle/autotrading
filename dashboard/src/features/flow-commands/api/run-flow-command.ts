import { useMutation, useQueryClient, type Query } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import type { FlowCommand } from '../utils/flow-transitions';

type RunFlowCommandOptions = {
  /** Called even if the page of the flow is gone by then, as an archived flow leaves the flows in use. */
  readonly onSuccess: (command: FlowCommand) => void;
};

// The list of the flows and every read of this flow show its status, its positions or its cycles (ADR 0132).
const readsTheFlow =
  (flowId: string) =>
  (query: Query): boolean =>
    query.queryKey[0] === 'flows' || query.queryKey.includes(flowId);

/** Sends a command of the user to the flow, then reads the flow again (R2.3.4). */
export const useRunFlowCommand = (flowId: string, { onSuccess }: RunFlowCommandOptions) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (command: FlowCommand) =>
      api.send('POST', `/flows/${encodeURIComponent(flowId)}/${command}`),
    onSuccess: (_answer, command) => onSuccess(command),
    onSettled: () => queryClient.invalidateQueries({ predicate: readsTheFlow(flowId) }),
  });
};
