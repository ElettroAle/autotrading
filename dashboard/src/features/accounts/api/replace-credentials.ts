import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

// The fields the exchange of the account declares: the API names the missing one by its label and checks the
// credentials with the exchange before saving them (R0.2.4, R2.3.9, ADR 0130).
export const credentialsInputSchema = z.object({ credentials: z.record(z.string(), z.string()) });

export type CredentialsInput = z.infer<typeof credentialsInputSchema>;

// The API answers with the account alone: its capital and network come with the list of the accounts.
const replacedAccountSchema = z.object({ id: z.string(), name: z.string() });

type CredentialsReplacement = {
  readonly accountId: string;
  readonly credentials: CredentialsInput['credentials'];
};

/** Replaces the credentials of an account; like the registration, it leaves nothing in the cache (ADR 0130). */
export const useReplaceCredentials = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, credentials }: CredentialsReplacement) =>
      readData(
        await api.PUT('/accounts/{account_id}/credentials', {
          params: { path: { account_id: accountId } },
          body: { credentials },
        }),
        replacedAccountSchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
