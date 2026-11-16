import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { TableFilterValues } from '@/hooks/use-table-filters';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

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
  total: z.number(),
  cycles: z.array(cycleSummarySchema),
});

export type CycleSummary = z.infer<typeof cycleSummarySchema>;

/**
 * The cycles of a flow that match the filters, from the most recent, in the pages of the API, with how many match in
 * all (R1.7.3, R6.4.4). The page shown stays while the next filters are read.
 */
export const useCycles = (flowId: string, page: number, filters: TableFilterValues) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('cycles', flowId, page, filters),
    placeholderData: keepPreviousData,
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/cycles', {
          params: {
            path: { flow_id: flowId },
            query: { page, outcome: filters.outcome, decision: filters.decision },
          },
        }),
        cyclePageSchema,
      ),
  });
};
