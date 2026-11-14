import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

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
  recent_outcomes: z.array(cycleOutcomeSchema),
});

export type CycleOutcome = z.infer<typeof cycleOutcomeSchema>;

export type FlowOverview = z.infer<typeof flowOverviewSchema>;

/** The flows in use of the tenant with their state, their recent cycles and their capital (R1.7.3, ADR 0127). */
export const useFlowOverviews = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['flows', 'overview'],
    queryFn: () => api.get('/flows/overview', z.array(flowOverviewSchema)),
  });
};
