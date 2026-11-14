import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, isComplete, type Period } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const rowSchema = z.object({
  flow_id: z.string(),
  flow_name: z.string(),
  return_percent: z.string().nullable(),
  max_drawdown_percent: z.string(),
  pnl: z.string(),
  total_fees: z.string(),
  win_rate_percent: z.string().nullable(),
  operations: z.number(),
  model_cost_usd: z.string(),
  model_calls_without_cost: z.number(),
});

export type FlowRankingRow = z.infer<typeof rowSchema>;

const rankingSchema = z.array(rowSchema);

/** The ranking of the flows over a period, as the API computes it (ADR 0135); a range waits for both its days. */
export const useFlowRanking = (period: Period) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-ranking', period),
    queryFn: async () =>
      readData(
        await api.GET('/flows/ranking', { querySerializer: () => apiSearchOf(period) }),
        rankingSchema,
      ),
    enabled: isComplete(period),
  });
};
