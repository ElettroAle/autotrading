import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readData, useApiClient } from '@/lib/api-client';

import { FLOWS_QUERY_KEY, flowsSchema, type Flow } from './get-flows';

const flowSchema = flowsSchema.element;

/** A draft with the strategy of the flow, to try a variant of it (R2.4.1, ADR 0125). */
export const useDuplicateFlow = ({ onSuccess }: { onSuccess: (copy: Flow) => void }) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (flowId: string) =>
      readData(
        await api.POST('/flows/{flow_id}/duplicate', { params: { path: { flow_id: flowId } } }),
        flowSchema,
      ),
    onSuccess: async (copy) => {
      await queryClient.invalidateQueries({ queryKey: FLOWS_QUERY_KEY });
      onSuccess(copy);
    },
  });
};
