import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { reconciliationQueryKey } from './get-account-reconciliation';

const DECIMAL = /^\d+([.,]\d+)?$/;

/** What the user writes: a number, with a decimal comma or point; its range is the API's to check (R3.3.1). */
export const thresholdInputSchema = z.object({
  percent: z
    .string()
    .trim()
    .regex(DECIMAL, 'scrivi la soglia in percento, per esempio 1 oppure 0,5'),
});

export type ThresholdInput = z.infer<typeof thresholdInputSchema>;

const thresholdSchema = z.object({ percent: z.string() });

/** The threshold of the balance deviation of an account, in percent of the expected balance (R3.3.2). */
export const useSetDeviationThreshold = (accountId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ percent }: ThresholdInput) =>
      readData(
        await api.PUT('/accounts/{account_id}/deviation-threshold', {
          params: { path: { account_id: accountId } },
          // The percent travels as text, so no digit is rounded on the way (ADR 0018).
          body: { percent: percent.trim().replace(',', '.') },
        }),
        thresholdSchema,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reconciliationQueryKey(accountId) }),
  });
};
