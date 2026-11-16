import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const flowOpeningsSchema = z.object({
  suspension: z.object({ reason: z.string(), suspended_at: z.string() }).nullable(),
});

export type FlowOpenings = z.infer<typeof flowOpeningsSchema>;

/** The openings of the flow suspended for maximum loss now, as the API decides it, or none (R3.2.2, ADR 0116). */
export const useFlowOpenings = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-openings', flowId),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/openings', { params: { path: { flow_id: flowId } } }),
        flowOpeningsSchema,
      ),
  });
};
