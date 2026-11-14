import { useMutation, useQueryClient, type Query } from '@tanstack/react-query';

import { readDone, useApiClient, type ApiClient } from '@/lib/api-client';

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

// Stop and archive have their own functions in the API; the other commands share one (R1.1.4-R1.1.6).
const sendCommand = (api: ApiClient, flowId: string, command: FlowCommand) => {
  const params = { path: { flow_id: flowId } };
  if (command === 'stop') {
    return api.POST('/flows/{flow_id}/stop', { params });
  }
  if (command === 'archive') {
    return api.POST('/flows/{flow_id}/archive', { params });
  }
  return api.POST('/flows/{flow_id}/{action}', {
    params: { path: { flow_id: flowId, action: command } },
  });
};

/** Sends a command of the user to the flow, then reads the flow again (R2.3.4). */
export const useRunFlowCommand = (flowId: string, { onSuccess }: RunFlowCommandOptions) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (command: FlowCommand) => readDone(await sendCommand(api, flowId, command)),
    onSuccess: (_answer, command) => onSuccess(command),
    onSettled: () => queryClient.invalidateQueries({ predicate: readsTheFlow(flowId) }),
  });
};
