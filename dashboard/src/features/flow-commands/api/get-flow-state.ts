import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const flowStateSchema = z.object({
  positions: z.array(z.object({ asset: z.string() })),
});

export type FlowState = z.infer<typeof flowStateSchema>;

/** The state of the flow read from the exchange now, with its open positions (R1.6.1). */
export const useFlowState = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['flow-state', flowId, 'assets'],
    queryFn: () => api.get(`/flows/${encodeURIComponent(flowId)}/state`, flowStateSchema),
  });
};
