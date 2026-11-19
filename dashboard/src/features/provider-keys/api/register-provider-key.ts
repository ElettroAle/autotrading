import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { dayOrNothing } from '@/utils/format-day';

import { PROVIDER_KEYS_QUERY_KEY, providerKeySchema } from './get-provider-keys';

const REQUIRED = 'Campo obbligatorio';

// Only presence: the API tells which providers it accepts, and never asks the provider about the key (R1.4.1).
export const providerKeyInputSchema = z.object({
  provider: z.string().trim().min(1, REQUIRED),
  // The fields the chosen provider declares: the API tells which one is missing, by its label (R2.3.9).
  key: z.record(z.string(), z.string()),
  // The day the key expires, when the user knows it (R6.2.2).
  expires_on: z.string().optional(),
});

export type ProviderKeyInput = z.infer<typeof providerKeyInputSchema>;

/** Registers the key of a provider; the key leaves nothing in the cache once the form resets it (ADR 0130). */
export const useRegisterProviderKey = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: ProviderKeyInput) =>
      readData(
        await api.POST('/provider-keys', {
          body: { ...input, expires_on: dayOrNothing(input.expires_on) },
        }),
        providerKeySchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROVIDER_KEYS_QUERY_KEY }),
  });
};
