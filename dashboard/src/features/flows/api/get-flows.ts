import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const flowSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
});

export type Flow = z.infer<typeof flowSchema>;

export const flowsSchema = z.array(flowSchema);

/** The flows of the tenant of the user: the API answers only with those (R0.1.3). */
export const useFlows = () => {
  const api = useApiClient();
  return useQuery({ queryKey: ['flows'], queryFn: () => api.get('/flows', flowsSchema) });
};
