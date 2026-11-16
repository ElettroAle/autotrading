import { useMutation, useQueryClient, type Query } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

// The list of the flows and every read of this flow show whether its openings are suspended (ADR
// perdita-massima-nella-dashboard).
const readsTheFlow =
  (flowId: string) =>
  (query: Query): boolean =>
    query.queryKey[0] === 'flows' || query.queryKey.includes(flowId);

/** Resumes the openings of the flow the user confirmed, then reads the flow again (R3.2.2). */
export const useResumeFlowOpenings = (flowId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      readDone(
        await api.POST('/flows/{flow_id}/openings/resume', {
          params: { path: { flow_id: flowId } },
        }),
      ),
    onSettled: () => queryClient.invalidateQueries({ predicate: readsTheFlow(flowId) }),
  });
};
