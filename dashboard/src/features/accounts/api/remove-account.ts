import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

type AccountRemoval = { readonly accountId: string; readonly confirmed: boolean };

/**
 * Removes an account in the two steps of the API (R0.2.5, R1.1.8): unconfirmed, it is refused with the reason when the
 * account has flows operating or open positions; confirmed, the removal goes on.
 */
export const useRemoveAccount = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, confirmed }: AccountRemoval) =>
      readDone(
        await api.DELETE('/accounts/{account_id}', {
          params: { path: { account_id: accountId }, query: confirmed ? { confirmed } : {} },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
