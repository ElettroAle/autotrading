import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { dayOrNothing } from '@/utils/format-day';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

const REQUIRED = 'Campo obbligatorio';

// Only presence: every rule on the values stays with the API, which answers with its reason (ADR 0130).
export const accountRegistrationInputSchema = z.object({
  name: z.string().trim().min(1, REQUIRED),
  exchange: z.string().trim().min(1, REQUIRED),
  // The fields the chosen exchange declares: the API tells which one is missing, by its label (R2.3.9).
  credentials: z.record(z.string(), z.string()),
  // The day the credentials expire, when the user knows it and the exchange does not read it (R6.2.2).
  expires_on: z.string().optional(),
});

export type AccountRegistrationInput = z.infer<typeof accountRegistrationInputSchema>;

const registeredAccountSchema = z.object({ id: z.string(), name: z.string() });

/**
 * Registers an account with its credentials. They travel in the variables of the mutation: with no time in the cache,
 * the mutation is dropped as soon as the form resets it (ADR 0130).
 */
export const useRegisterAccount = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: AccountRegistrationInput) =>
      readData(
        await api.POST('/accounts', {
          body: { ...input, expires_on: dayOrNothing(input.expires_on) },
        }),
        registeredAccountSchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
