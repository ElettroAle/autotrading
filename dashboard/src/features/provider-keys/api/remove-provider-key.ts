import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY } from './get-provider-keys';

/** Removes the key of a provider; the API refuses while flows not stopped use it (R1.4.1). */
export const useRemoveProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) =>
      api.send('DELETE', `/provider-keys/${encodeURIComponent(provider)}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
