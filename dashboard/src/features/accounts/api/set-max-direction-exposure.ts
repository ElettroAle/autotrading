import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

const DECIMAL = /^\d+([.,]\d+)?$/;

/** What the user writes: empty for no limit, or a number with a decimal comma or point; its range is the API's to check. */
export const exposureLimitInputSchema = z.object({
  percent: z
    .string()
    .trim()
    .refine(
      (text) => text === '' || DECIMAL.test(text),
      'scrivi il limite in percento, per esempio 60 oppure 62,5',
    ),
});

export type ExposureLimitInput = z.infer<typeof exposureLimitInputSchema>;

/** The percent the API receives: null takes the limit away. */
export const exposureLimitOf = ({ percent }: ExposureLimitInput): string | null => {
  const text = percent.trim();
  return text === '' ? null : text.replace(',', '.');
};

/**
 * The largest exposure the flows of the account may have together on one side, in percent of its balance; null takes
 * it away (R5.5.5, ADR esposizione-massima-per-direzione-del-conto).
 */
export const useSetMaxDirectionExposure = (accountId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (percent: string | null) =>
      readDone(
        await api.PUT('/accounts/{account_id}/max-direction-exposure', {
          params: { path: { account_id: accountId } },
          // The percent travels as text, so no digit is rounded on the way (ADR 0018).
          body: { percent },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ACCOUNTS_QUERY_KEY }),
  });
};
