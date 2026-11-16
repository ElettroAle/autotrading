import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { ListInterval } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const FAILED = 'fallito';

const failedPageSchema = z.object({
  has_next: z.boolean(),
  cycles: z.array(z.object({ planned_at: z.string() })),
});

/**
 * The instants of the failed cycles of the flow in the period, every page of the API, to mark them on the
 * equity curve (ADR cicli-falliti-sull-equity-curve).
 */
export const useFailedCycles = (flowId: string, interval: ListInterval) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'failed-cycles', interval),
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const instants: string[] = [];
      for (let page = 1; ; page += 1) {
        const read = readData(
          await api.GET('/flows/{flow_id}/cycles', {
            params: { path: { flow_id: flowId }, query: { page, outcome: FAILED, ...interval } },
          }),
          failedPageSchema,
        );
        instants.push(...read.cycles.map((cycle) => cycle.planned_at));
        if (!read.has_next) {
          return instants;
        }
      }
    },
  });
};
