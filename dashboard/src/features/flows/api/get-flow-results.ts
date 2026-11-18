import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, type Period } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

/**
 * How a flow is doing at a glance in a period, as the API measures it (R6.4.2, ADR riepilogo-dei-risultati-nell-api):
 * gains as text in the currency of the account (ADR 0018), percents of the initial capital, null when not measurable;
 * the next planned cycle, whatever the period, null unless the flow is active (R6.4.8).
 */
export const resultsSummarySchema = z.object({
  total_gain: z.string(),
  total_gain_percent: z.string().nullable(),
  period_gain: z.string(),
  period_gain_percent: z.string().nullable(),
  open_positions: z.number(),
  failed_cycles: z.number(),
  next_cycle_at: z.string().nullable(),
});

export type ResultsSummary = z.infer<typeof resultsSummarySchema>;

const flowResultsSchema = z.object({
  currency: z.string(),
  summary: resultsSummarySchema,
});

/** The results of a flow in the period of the page, from its state read now (R6.4.2). */
export const useFlowResults = (flowId: string, period: Period) => {
  const api = useApiClient();
  const search = apiSearchOf(period);
  return useQuery({
    ...pageDataQuery('flow-state', flowId, 'results', search),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', {
          params: { path: { flow_id: flowId } },
          querySerializer: () => search,
        }),
        flowResultsSchema,
      ),
    placeholderData: keepPreviousData,
  });
};
