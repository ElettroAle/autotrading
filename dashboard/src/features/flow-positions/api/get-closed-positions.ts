import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const closedPositionSchema = z.object({
  asset: z.string(),
  side: z.string(),
  open_price: z.string(),
  close_price: z.string(),
  opened_at: z.string(),
  closed_at: z.string(),
  pnl: z.string(),
  pnl_percent_of_margin: z.string(),
  fees: z.string(),
  reason: z.string(),
});

const closedPositionPageSchema = z.object({
  page: z.number(),
  has_next: z.boolean(),
  positions: z.array(closedPositionSchema),
});

export type ClosedPosition = z.infer<typeof closedPositionSchema>;

/** The closed positions of a flow from the most recent close, in the pages of the API (R1.7.2). */
export const useClosedPositions = (flowId: string, page: number) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('closed-positions', flowId, page),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/closed-positions', {
          params: { path: { flow_id: flowId }, query: { page } },
        }),
        closedPositionPageSchema,
      ),
  });
};
