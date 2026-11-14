import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

/** A draft has only the strategy: account, capital and assets come before it starts (ADR 0124). */
export const DRAFT_STATUS = 'bozza';

export const FLOWS_QUERY_KEY = ['flows'];

const flowSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  account_id: z.string().nullable(),
  version: z.number(),
  assets: z.array(z.string()),
  allocated_capital: z.string().nullable(),
  model: z.object({ name: z.string() }),
  sources: z.array(z.object({ name: z.string(), weight: z.number() })),
});

export type Flow = z.infer<typeof flowSchema>;

export const flowsSchema = z.array(flowSchema);

/** The flows of the tenant of the user: the API answers only with those (R0.1.3). */
export const useFlows = () => {
  const api = useApiClient();
  return useQuery({ queryKey: FLOWS_QUERY_KEY, queryFn: () => api.get('/flows', flowsSchema) });
};
