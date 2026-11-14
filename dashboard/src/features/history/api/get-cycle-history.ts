import { z } from 'zod';

import { readData } from '@/lib/api-client';

import { useHistoryPages } from './history-pages';

const historyCycleSchema = z.object({
  flow_id: z.string(),
  flow: z.string(),
  version: z.number().nullable(),
  planned_at: z.string(),
  started_at: z.string().nullable(),
  outcome: z.string(),
  failure: z.object({ step: z.string(), error_type: z.string(), message: z.string() }).nullable(),
});

const cyclesPageSchema = z.object({
  cycles: z.array(historyCycleSchema),
  next: z.string().nullable(),
});

export type HistoryCycle = z.infer<typeof historyCycleSchema>;

/** The cycles of the flows of the user that match the search, from the most recent (R2.5.1). */
export const useCycleHistory = (query: string, enabled: boolean) =>
  useHistoryPages(
    'cycles',
    query,
    async (api, search) =>
      readData(
        await api.GET('/history/cycles', { querySerializer: () => search }),
        cyclesPageSchema,
      ),
    enabled,
  );
