import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const flowStateSchema = z.object({
  positions: z.array(z.object({ asset: z.string() })),
});

export type FlowState = z.infer<typeof flowStateSchema>;

/** The state of the flow read from the exchange now, with its open positions (R1.6.1). */
export const useFlowState = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-state', flowId, 'assets'),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', { params: { path: { flow_id: flowId } } }),
        flowStateSchema,
      ),
  });
};
