import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY, providerKeySchema } from './get-provider-keys';

const REQUIRED = 'Campo obbligatorio';

// Only presence: the API tells which providers it accepts, and never asks the provider about the key (R1.4.1).
export const providerKeyInputSchema = z.object({
  provider: z.string().trim().min(1, REQUIRED),
  key: z.string().min(1, REQUIRED),
});

export type ProviderKeyInput = z.infer<typeof providerKeyInputSchema>;

/** Registers the key of a provider; the key leaves nothing in the cache once the form resets it (ADR 0130). */
export const useRegisterProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: ProviderKeyInput) =>
      readData(await api.POST('/provider-keys', { body: input }), providerKeySchema),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
