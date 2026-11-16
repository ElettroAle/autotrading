import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { ListInterval } from '@/components/ui/period-selector/use-period';
import type { TableFilterValues } from '@/hooks/use-table-filters';
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
  total: z.number(),
  positions: z.array(closedPositionSchema),
});

export type ClosedPosition = z.infer<typeof closedPositionSchema>;

/**
 * The closed positions of a flow that match the filters, from the most recent close, in the pages of the API, with how
 * many match in all (R1.7.2, R6.4.4). The page shown stays while the next filters are read.
 */
export const useClosedPositions = (
  flowId: string,
  page: number,
  filters: TableFilterValues,
  interval: ListInterval,
) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('closed-positions', flowId, page, filters, interval),
    placeholderData: keepPreviousData,
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/closed-positions', {
          params: {
            path: { flow_id: flowId },
            query: {
              page,
              asset: filters.asset,
              side: filters.side,
              result: filters.result,
              ...interval,
            },
          },
        }),
        closedPositionPageSchema,
      ),
  });
};
