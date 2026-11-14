import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, isComplete, type Period } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const statisticsSchema = z.object({
  won: z.number(),
  lost: z.number(),
  operations: z.number(),
  win_rate_percent: z.string().nullable(),
  average_winning_pnl: z.string().nullable(),
  average_losing_pnl: z.string().nullable(),
  total_fees: z.string(),
  model_cost_usd: z.string(),
  model_calls_without_cost: z.number(),
});

export type FlowStatistics = z.infer<typeof statisticsSchema>;

/** The statistics of a flow over a period, as the API computes them (ADR 0122); a range waits for both its days. */
export const useFlowStatistics = (flowId: string, period: Period) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-statistics', flowId, period),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/statistics', {
          params: { path: { flow_id: flowId } },
          querySerializer: () => apiSearchOf(period),
        }),
        statisticsSchema,
      ),
    enabled: isComplete(period),
  });
};
