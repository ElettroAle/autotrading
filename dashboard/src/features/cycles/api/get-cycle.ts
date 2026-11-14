import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

import { failureSchema } from './get-cycles';

const cycleSchema = z.object({
  planned_at: z.string(),
  started_at: z.string().nullable(),
  delay_seconds: z.number().nullable(),
  outcome: z.string(),
  failure: failureSchema.nullable(),
  steps: z.array(z.string()),
  absent_sources: z.array(z.object({ source: z.string(), reason: z.string() })),
  documents: z.array(z.object({ step: z.string(), content: z.record(z.string(), z.unknown()) })),
  cost: z
    .object({
      input_tokens: z.number(),
      output_tokens: z.number(),
      cost_usd: z.string().nullable(),
    })
    .nullable(),
});

export type Cycle = z.infer<typeof cycleSchema>;
export type StepDocument = Cycle['documents'][number];

/** A cycle with everything recorded about it (R1.7.1). */
export const useCycle = (flowId: string, plannedAt: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['cycle', flowId, plannedAt],
    queryFn: () =>
      api.get(
        `/flows/${encodeURIComponent(flowId)}/cycles/${encodeURIComponent(plannedAt)}`,
        cycleSchema,
      ),
  });
};
