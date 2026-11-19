import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { dayOrNothing } from '@/utils/format-day';

import { PROVIDER_KEYS_QUERY_KEY, providerKeySchema } from './get-provider-keys';

// The fields the provider declares for its key: the API names the missing one (R2.3.9, ADR 0130).
// The day the new key expires, when the user knows it: without it the key has no date (R6.2.2).
export const newKeyInputSchema = z.object({
  key: z.record(z.string(), z.string()),
  expires_on: z.string().optional(),
});

export type NewKeyInput = z.infer<typeof newKeyInputSchema>;

type ProviderKeyReplacement = NewKeyInput & { readonly provider: string };

/** Puts a new key in place of the one of the provider; nothing stays in the cache (ADR 0130). */
export const useReplaceProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ provider, key, expires_on }: ProviderKeyReplacement) =>
      readData(
        await api.PUT('/provider-keys/{provider}', {
          params: { path: { provider } },
          body: { key, expires_on: dayOrNothing(expires_on) },
        }),
        providerKeySchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
