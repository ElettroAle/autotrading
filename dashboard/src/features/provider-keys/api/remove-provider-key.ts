import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY } from './get-provider-keys';

/** Removes the key of a provider; the API refuses while flows not stopped use it (R1.4.1). */
export const useRemoveProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (provider: string) =>
      readDone(await api.DELETE('/provider-keys/{provider}', { params: { path: { provider } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
