import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

const REQUIRED = 'Campo obbligatorio';

// Only presence: every rule on the values stays with the API, which answers with its reason (ADR 0130).
export const accountRegistrationInputSchema = z.object({
  name: z.string().trim().min(1, REQUIRED),
  exchange: z.string().trim().min(1, REQUIRED),
  account_address: z.string().trim().min(1, REQUIRED),
  secret_key: z.string().min(1, REQUIRED),
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
    mutationFn: (input: AccountRegistrationInput) =>
      api.write('POST', '/accounts', input, registeredAccountSchema),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
