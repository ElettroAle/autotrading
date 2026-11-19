import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { dayOrNothing } from '@/utils/format-day';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

// The fields the exchange of the account declares: the API names the missing one by its label and checks the
// credentials with the exchange before saving them (R0.2.4, R2.3.9, ADR 0130).
// The day the new credentials expire, only where the exchange does not read it (R6.2.2).
export const credentialsInputSchema = z.object({
  credentials: z.record(z.string(), z.string()),
  expires_on: z.string().optional(),
});

export type CredentialsInput = z.infer<typeof credentialsInputSchema>;

// The API answers with the account alone: its capital and network come with the list of the accounts.
const replacedAccountSchema = z.object({ id: z.string(), name: z.string() });

type CredentialsReplacement = CredentialsInput & { readonly accountId: string };

/** Replaces the credentials of an account; like the registration, it leaves nothing in the cache (ADR 0130). */
export const useReplaceCredentials = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, credentials, expires_on }: CredentialsReplacement) =>
      readData(
        await api.PUT('/accounts/{account_id}/credentials', {
          params: { path: { account_id: accountId } },
          body: { credentials, expires_on: dayOrNothing(expires_on) },
        }),
        replacedAccountSchema,
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
