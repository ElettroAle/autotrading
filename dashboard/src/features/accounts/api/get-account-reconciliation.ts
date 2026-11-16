import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { ACCOUNTS_QUERY_KEY } from './get-accounts';

const balanceComparisonSchema = z.object({
  compared_at: z.string(),
  expected_balance: z.string(),
  read_balance: z.string(),
  deviation_percent: z.string(),
});

export const reconciliationAlarmSchema = z.object({
  expected_balance: z.string(),
  read_balance: z.string(),
  deviation_percent: z.string(),
  opened_at: z.string(),
  confirmed_at: z.string().nullable(),
});

export type ReconciliationAlarm = z.infer<typeof reconciliationAlarmSchema>;

// Whether the balance is the expected one is the API's: the dashboard shows it (ADR
// stato-della-riconciliazione-nella-dashboard).
const accountReconciliationSchema = z.object({
  aligned: z.boolean(),
  threshold_percent: z.string(),
  last_comparison: balanceComparisonSchema.nullable(),
  open_alarm: reconciliationAlarmSchema.nullable(),
});

export type AccountReconciliation = z.infer<typeof accountReconciliationSchema>;

/** The key of what the API says of the reconciliation of an account: its commands invalidate it. */
export const reconciliationQueryKey = (accountId: string) =>
  [...ACCOUNTS_QUERY_KEY, accountId, 'reconciliation'] as const;

/** The reconciliation of the balance of an account: last comparison, threshold and open alarm (R3.3.2). */
export const useAccountReconciliation = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts', accountId, 'reconciliation'),
    queryFn: async () =>
      readData(
        await api.GET('/accounts/{account_id}/reconciliation', {
          params: { path: { account_id: accountId } },
        }),
        accountReconciliationSchema,
      ),
  });
};
