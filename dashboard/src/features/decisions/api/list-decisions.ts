import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, type Period } from '@/components/ui/period-selector/use-period';
import type { TableFilterValues } from '@/hooks/use-table-filters';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const decisionSchema = z.object({
  planned_at: z.string(),
  asset: z.string(),
  action: z.string(),
  direction: z.string().nullable(),
  confidence: z.number().nullable(),
  reasoning: z.string(),
});

const decisionPageSchema = z.object({
  page: z.number(),
  has_next: z.boolean(),
  total: z.number(),
  decisions: z.array(decisionSchema),
});

export type DatedDecision = z.infer<typeof decisionSchema>;

/**
 * The decisions of the completed cycles of a flow in the period of the page that match the filters, one by cycle and
 * asset, from the most recent, in the pages of the API, with how many match in all (ADR
 * storico-delle-decisioni-nell-api). The period goes as the API reads it, the last days counted by the API; the page
 * shown stays while the next filters are read.
 */
export const useDecisions = (
  flowId: string,
  page: number,
  filters: TableFilterValues,
  period: Period,
) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('decisions', flowId, page, filters, period),
    placeholderData: keepPreviousData,
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/decisions', {
          params: {
            path: { flow_id: flowId },
            query: {
              page,
              asset: filters.asset,
              action: filters.action,
              direction: filters.direction,
              ...Object.fromEntries(new URLSearchParams(apiSearchOf(period))),
            },
          },
        }),
        decisionPageSchema,
      ),
  });
};
