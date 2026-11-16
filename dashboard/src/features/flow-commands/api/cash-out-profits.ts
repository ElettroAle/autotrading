import { useMutation, useQueryClient, type Query } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const cashOutOutcomeSchema = z.object({
  freed: z.string().nullable(),
  left_open: z.array(z.object({ asset: z.string(), reason: z.string() })),
});

export type CashOutOutcome = z.infer<typeof cashOutOutcomeSchema>;

// The cash-out closes the positions of the flow and changes its capital and the free capital of its account
// (ADR incasso-dei-profitti-nella-dashboard).
const readsTheFlowOrItsAccount =
  (flowId: string) =>
  (query: Query): boolean =>
    query.queryKey[0] === 'flows' ||
    query.queryKey[0] === 'accounts' ||
    query.queryKey.includes(flowId);

/** Cashes out the profits of the flow, keeping the capital given or the capital allocated now (R3.4.1). */
export const useCashOutProfits = (flowId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (capital: string | null) =>
      readData(
        await api.POST('/flows/{flow_id}/cash-out', {
          params: { path: { flow_id: flowId } },
          body: { capital },
        }),
        cashOutOutcomeSchema,
      ),
    onSettled: () => queryClient.invalidateQueries({ predicate: readsTheFlowOrItsAccount(flowId) }),
  });
};
