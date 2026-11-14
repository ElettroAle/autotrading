import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

// Numbers of the configuration travel as strings, so no precision is lost on the way (ADR 0018).
export const flowSchema = z.object({
  id: z.string(),
  name: z.string(),
  account_id: z.string().nullable(),
  status: z.string(),
  version: z.number(),
  assets: z.array(z.string()),
  cycle_minutes: z.number(),
  model: z.object({ name: z.string(), parameters: z.record(z.string(), z.string()) }),
  sources: z.array(
    z.object({
      name: z.string(),
      weight: z.number(),
      parameters: z.record(z.string(), z.number()),
    }),
  ),
  instructions: z.string(),
  risk_limits: z.object({
    max_leverage: z.number().nullable(),
    max_margin_exposure_percent: z.string().nullable(),
    max_value_exposure_percent: z.string().nullable(),
  }),
  allocated_capital: z.string().nullable(),
  bring_to_minimum: z.boolean(),
});

export type Flow = z.infer<typeof flowSchema>;

/** The flow with the configuration version in force; the API lists only the flows of the tenant (R0.1.3). */
export const useFlow = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    // Its own key under the flows: the list elsewhere keeps less of each flow, and both refresh together.
    queryKey: ['flows', 'configurations'],
    queryFn: async () => readData(await api.GET('/flows'), z.array(flowSchema)),
    select: (flows) => flows.find((flow) => flow.id === flowId),
  });
};
