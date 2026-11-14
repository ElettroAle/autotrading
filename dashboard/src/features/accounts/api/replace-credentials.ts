import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY, accountSchema } from './get-accounts';

const REQUIRED = 'Campo obbligatorio';

// Only presence: the API checks the credentials with the exchange before saving them (R0.2.4, ADR 0130).
export const credentialsInputSchema = z.object({
  account_address: z.string().trim().min(1, REQUIRED),
  secret_key: z.string().min(1, REQUIRED),
});

export type CredentialsInput = z.infer<typeof credentialsInputSchema>;

type CredentialsReplacement = {
  readonly accountId: string;
  readonly credentials: CredentialsInput;
};

/** Replaces the credentials of an account; like the registration, it leaves nothing in the cache (ADR 0130). */
export const useReplaceCredentials = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, credentials }: CredentialsReplacement) =>
      api.write(
        'PUT',
        `/accounts/${encodeURIComponent(accountId)}/credentials`,
        credentials,
        accountSchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
