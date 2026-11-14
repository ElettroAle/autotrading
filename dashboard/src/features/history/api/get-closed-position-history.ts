import { z } from 'zod';

import { readData } from '@/lib/api-client';

import { useHistoryPages } from './history-pages';

const historyPositionSchema = z.object({
  id: z.string(),
  flow: z.string(),
  asset: z.string(),
  side: z.string(),
  leverage: z.number(),
  open_price: z.string(),
  close_price: z.string(),
  closed_at: z.string(),
  pnl: z.string(),
  pnl_percent_of_margin: z.string(),
  fees: z.string(),
  reason: z.string(),
});

const positionsPageSchema = z.object({
  positions: z.array(historyPositionSchema),
  next: z.string().nullable(),
});

export type HistoryPosition = z.infer<typeof historyPositionSchema>;

/** The closed positions of the flows of the user that match the search, from the most recent close (R2.5.1). */
export const useClosedPositionHistory = (query: string, enabled: boolean) =>
  useHistoryPages(
    'closed-positions',
    query,
    async (api, search) =>
      readData(
        await api.GET('/history/closed-positions', { querySerializer: () => search }),
        positionsPageSchema,
      ),
    enabled,
  );
