import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

type AccountKeyExpiry = { readonly accountId: string; readonly expiresOn: string | null };

/** The day the credentials of the account expire, given by the user where the exchange does not read it (R6.2.2). */
export const useSetAccountKeyExpiry = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, expiresOn }: AccountKeyExpiry) =>
      readDone(
        await api.PUT('/accounts/{account_id}/expiry', {
          params: { path: { account_id: accountId } },
          body: { expires_on: expiresOn },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
