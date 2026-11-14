import { z } from 'zod';

import { readData } from '@/lib/api-client';

import { useHistoryPages } from './history-pages';

const executionSchema = z.object({
  executed_at: z.string(),
  price: z.string(),
  size: z.string(),
  fee: z.string(),
});

const historyOrderSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  account: z.string(),
  flow: z.string().nullable(),
  asset: z.string(),
  direction: z.string(),
  closing: z.boolean(),
  status: z.string(),
  executions: z.array(executionSchema),
});

const ordersPageSchema = z.object({
  orders: z.array(historyOrderSchema),
  next: z.string().nullable(),
});

export type HistoryOrder = z.infer<typeof historyOrderSchema>;
export type HistoryExecution = z.infer<typeof executionSchema>;

/** The orders on the accounts of the user that match the search, with their executions, newest first (R2.5.1). */
export const useOrderHistory = (query: string, enabled: boolean) =>
  useHistoryPages(
    'orders',
    query,
    async (api, search) =>
      readData(
        await api.GET('/history/orders', { querySerializer: () => search }),
        ordersPageSchema,
      ),
    enabled,
  );
