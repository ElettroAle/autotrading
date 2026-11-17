import { useMutation, useQueryClient, type Query } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const cycleRunSchema = z.object({ planned_at: z.string(), outcome: z.string() });

export type CycleRun = z.infer<typeof cycleRunSchema>;

// The cycle may have changed the cycles, the state, the overview and the equity of the flow
// (ADR pulsante-esegui-ora-nella-pagina-del-flusso).
const readsTheFlow =
  (flowId: string) =>
  (query: Query): boolean =>
    query.queryKey[0] === 'flows' || query.queryKey.includes(flowId);

/** Asks the worker for a full cycle of the flow now and answers once it ends, failed or not (R6.5.2). */
export const useRunCycleNow = (flowId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      readData(
        await api.POST('/flows/{flow_id}/cycles', { params: { path: { flow_id: flowId } } }),
        cycleRunSchema,
      ),
    onSettled: () => queryClient.invalidateQueries({ predicate: readsTheFlow(flowId) }),
  });
};
