import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

// Only presence: whether the balance is above zero is the API's to say, with its reason (ADR 0130).
export const virtualBalanceInputSchema = z.object({
  balance: z.string().trim().min(1, 'Campo obbligatorio'),
});

export type VirtualBalanceInput = z.infer<typeof virtualBalanceInputSchema>;

/**
 * Starts an account of an exchange that holds a virtual balance again from the balance given: its positions closed and
 * its orders cancelled (R6.3.2). Every reading of the accounts, the balance read from the exchange included, is stale.
 */
export const useResetVirtualBalance = (accountId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ balance }: VirtualBalanceInput) =>
      readDone(
        await api.PUT('/accounts/{account_id}/virtual-balance', {
          params: { path: { account_id: accountId } },
          // The amount travels as text, so no digit is rounded on the way (ADR 0018).
          body: { balance: balance.trim().replace(',', '.') },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
