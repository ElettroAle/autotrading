import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const cyclePageSchema = z.object({
  cycles: z.array(z.object({ planned_at: z.string(), outcome: z.string() })),
});

export type CycleSummary = z.infer<typeof cyclePageSchema>['cycles'][number];

/** The first page of the cycles of the flow, from the most recent (R1.7.3). */
export const useRecentCycles = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'cycles'),
    queryFn: async () => {
      const page = readData(
        await api.GET('/flows/{flow_id}/cycles', { params: { path: { flow_id: flowId } } }),
        cyclePageSchema,
      );
      return page.cycles;
    },
  });
};
