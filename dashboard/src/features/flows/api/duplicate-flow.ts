import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import { FLOWS_QUERY_KEY, flowsSchema, type Flow } from './get-flows';

const flowSchema = flowsSchema.element;

/** A draft with the strategy of the flow, to try a variant of it (R2.4.1, ADR 0125). */
export const useDuplicateFlow = ({ onSuccess }: { onSuccess: (copy: Flow) => void }) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (flowId: string) =>
      api.post(`/flows/${encodeURIComponent(flowId)}/duplicate`, flowSchema),
    onSuccess: async (copy) => {
      await queryClient.invalidateQueries({ queryKey: FLOWS_QUERY_KEY });
      onSuccess(copy);
    },
  });
};
