import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY, providerKeySchema } from './get-provider-keys';

export const newKeyInputSchema = z.object({ key: z.string().min(1, 'Campo obbligatorio') });

export type NewKeyInput = z.infer<typeof newKeyInputSchema>;

type ProviderKeyReplacement = { readonly provider: string; readonly key: string };

/** Puts a new key in place of the one of the provider; nothing stays in the cache (ADR 0130). */
export const useReplaceProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ provider, key }: ProviderKeyReplacement) =>
      readData(
        await api.PUT('/provider-keys/{provider}', {
          params: { path: { provider } },
          body: { key },
        }),
        providerKeySchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
