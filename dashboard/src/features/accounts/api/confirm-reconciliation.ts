import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { reconciliationQueryKey } from './get-account-reconciliation';

/** The user has checked the balance of the account: the API closes its alarm and the openings resume (R3.3.1). */
export const useConfirmReconciliation = (accountId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      readDone(
        await api.POST('/accounts/{account_id}/reconciliation/confirmation', {
          params: { path: { account_id: accountId } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reconciliationQueryKey(accountId) }),
  });
};
