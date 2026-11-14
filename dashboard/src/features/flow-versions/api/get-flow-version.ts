import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const configurationSchema = z.object({
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

export type Configuration = z.infer<typeof configurationSchema>;

/** One configuration version of the flow, read as the API keeps it (R1.1.3). */
export const useFlowVersion = (flowId: string, version: number) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'versions', version),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/versions/{version}', {
          params: { path: { flow_id: flowId, version } },
        }),
        configurationSchema,
      ),
  });
};
