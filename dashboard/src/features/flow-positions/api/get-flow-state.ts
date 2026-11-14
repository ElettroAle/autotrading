import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const openPositionSchema = z.object({
  asset: z.string(),
  side: z.string(),
  size: z.string(),
  leverage: z.string(),
  entry_price: z.string(),
  margin: z.string(),
  unrealized_pnl: z.string(),
  unrealized_pnl_percent: z.string().nullable(),
});

const flowStateSchema = z.object({
  currency: z.string(),
  positions: z.array(openPositionSchema),
});

export type OpenPosition = z.infer<typeof openPositionSchema>;

/** The state of the flow read from the exchange at the request, with its open positions (R1.6.1). */
export const useFlowState = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-state', flowId),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', { params: { path: { flow_id: flowId } } }),
        flowStateSchema,
      ),
  });
};
