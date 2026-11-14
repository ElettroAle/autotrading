import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

export const failureSchema = z.object({
  step: z.string(),
  error_type: z.string(),
  message: z.string(),
});

const cycleSummarySchema = z.object({
  planned_at: z.string(),
  started_at: z.string().nullable(),
  outcome: z.string(),
  failure: failureSchema.nullable(),
  decisions: z.record(z.string(), z.unknown()).nullable(),
});

const cyclePageSchema = z.object({
  page: z.number(),
  has_next: z.boolean(),
  cycles: z.array(cycleSummarySchema),
});

export type CycleSummary = z.infer<typeof cycleSummarySchema>;

/** The cycles of a flow from the most recent, in the pages of the API (R1.7.3). */
export const useCycles = (flowId: string, page: number) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['cycles', flowId, page],
    queryFn: () =>
      api.get(`/flows/${encodeURIComponent(flowId)}/cycles?page=${page}`, cyclePageSchema),
  });
};
