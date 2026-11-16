import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { ListDays } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const capitalChangeSchema = z.object({
  changed_at: z.string(),
  flow_id: z.string().nullable(),
  flow: z.string().nullable(),
  reason: z.string(),
  amount: z.string(),
  previous: z.string().nullable(),
  new: z.string().nullable(),
});

const capitalChangePageSchema = z.object({
  page: z.number(),
  has_next: z.boolean(),
  total: z.number(),
  currency: z.string(),
  changes: z.array(capitalChangeSchema),
});

export type CapitalChange = z.infer<typeof capitalChangeSchema>;

export type CapitalChangePage = z.infer<typeof capitalChangePageSchema>;

/**
 * The changes of the capital of a flow in the days asked, from the most recent, in the pages of the API (R3.4.2). The
 * page shown stays while the next one is read.
 */
export const useFlowCapitalChanges = (flowId: string, page: number, days: ListDays) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-capital-changes', flowId, page, days),
    placeholderData: keepPreviousData,
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/capital-changes', {
          params: { path: { flow_id: flowId }, query: { page, ...days } },
        }),
        capitalChangePageSchema,
      ),
  });
};

/**
 * The changes of the capital of every flow of an account and the deposits and withdrawals its exchange declares, in the
 * days asked, from the most recent, in the pages of the API (R3.4.2).
 */
export const useAccountCapitalChanges = (accountId: string, page: number, days: ListDays) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('account-capital-changes', accountId, page, days),
    placeholderData: keepPreviousData,
    queryFn: async () =>
      readData(
        await api.GET('/accounts/{account_id}/capital-changes', {
          params: { path: { account_id: accountId }, query: { page, ...days } },
        }),
        capitalChangePageSchema,
      ),
  });
};
