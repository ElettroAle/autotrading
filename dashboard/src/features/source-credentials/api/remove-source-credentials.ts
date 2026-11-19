import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { SOURCE_CREDENTIALS_QUERY_KEY } from './get-source-credentials';

/** Removes the credentials of the adapter: the flows can no longer activate it (R4.1.2). */
export const useRemoveSourceCredentials = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (adapter: string) =>
      readDone(
        await api.DELETE('/source-credentials/{adapter}', { params: { path: { adapter } } }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SOURCE_CREDENTIALS_QUERY_KEY }),
  });
};
