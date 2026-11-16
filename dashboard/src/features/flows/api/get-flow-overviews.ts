import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, isComplete, type Period } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { resultsSummarySchema } from './get-flow-results';

const cycleOutcomeSchema = z.object({
  planned_at: z.string(),
  outcome: z.string(),
});

const flowOverviewSchema = z.object({
  id: z.string(),
  name: z.string(),
  account: z.string(),
  environment: z.string(),
  status: z.string(),
  pause_reason: z.string().nullable(),
  model: z.string(),
  version: z.number(),
  last_cycle: cycleOutcomeSchema.nullable(),
  next_cycle_at: z.string().nullable(),
  currency: z.string().nullable(),
  initial_capital: z.string().nullable(),
  current_capital: z.string().nullable(),
  return_percent: z.string().nullable(),
  // A draft has no account yet, so no results (ADR 0124).
  summary: resultsSummarySchema.nullable(),
});

export type FlowOverview = z.infer<typeof flowOverviewSchema>;

/**
 * The flows in use of the tenant with their state, their last cycle, their capital and their results in the period
 * chosen above the list (R1.7.3, ADR 0127, R6.4.2). A range waits for both its days, the list keeping what it read.
 */
export const useFlowOverviews = (period: Period) => {
  const api = useApiClient();
  const search = apiSearchOf(period);
  return useQuery({
    ...pageDataQuery('flows', 'overview', search),
    queryFn: async () =>
      readData(
        await api.GET('/flows/overview', { querySerializer: () => search }),
        z.array(flowOverviewSchema),
      ),
    enabled: isComplete(period),
    placeholderData: keepPreviousData,
  });
};
