import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

const WHOLE_NUMBER = /^\d+$/;

/** What the user writes: a whole number of minutes; its range is the API's to check. */
export const intervalInputSchema = z.object({
  minutes: z
    .string()
    .trim()
    .refine(
      (text) => WHOLE_NUMBER.test(text),
      'scrivi i minuti come numero intero, per esempio 15',
    ),
});

export type IntervalInput = z.infer<typeof intervalInputSchema>;

/**
 * How often, in minutes, the periodic check reconciles the account while its flows hold open positions (Bug 778, ADR
 * intervallo-di-riconciliazione-del-conto).
 */
export const useSetReconciliationInterval = (accountId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (minutes: number) =>
      readDone(
        await api.PUT('/accounts/{account_id}/reconciliation-interval', {
          params: { path: { account_id: accountId } },
          body: { minutes },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
