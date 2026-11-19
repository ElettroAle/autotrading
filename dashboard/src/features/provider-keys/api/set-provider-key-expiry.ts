import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY } from './get-provider-keys';

type ProviderKeyExpiry = { readonly provider: string; readonly expiresOn: string | null };

/** The day the key of the provider expires, given by the user; none forgets it (R6.2.2). */
export const useSetProviderKeyExpiry = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ provider, expiresOn }: ProviderKeyExpiry) =>
      readDone(
        await api.PUT('/provider-keys/{provider}/expiry', {
          params: { path: { provider } },
          body: { expires_on: expiresOn },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
