import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readData, useApiClient } from '@/lib/api-client';

import { FLOWS_QUERY_KEY, flowsSchema } from './get-flows';

/** The existing start of a flow: for a draft the API checks account, capital, assets and conflicts (ADR 0124). */
export const useStartFlow = (flowId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      readData(
        await api.POST('/flows/{flow_id}/{action}', {
          params: { path: { flow_id: flowId, action: 'start' } },
        }),
        flowsSchema.element,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FLOWS_QUERY_KEY }),
  });
};
