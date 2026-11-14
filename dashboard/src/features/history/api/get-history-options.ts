import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const flowOptionSchema = z.object({
  id: z.string(),
  name: z.string(),
  account_id: z.string(),
  version: z.number(),
  assets: z.array(z.string()),
});

const accountOptionSchema = z.object({ id: z.string(), name: z.string() });

export type FlowOption = z.infer<typeof flowOptionSchema>;
export type AccountOption = z.infer<typeof accountOptionSchema>;

/** The flows of the user, with their assets and their last version: the choices of the filters. */
export const useFlowOptions = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['history-options', 'flows'],
    queryFn: () => api.get('/flows', z.array(flowOptionSchema)),
  });
};

/** The accounts of the user: the choices of the filter by account. */
export const useAccountOptions = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['history-options', 'accounts'],
    queryFn: () => api.get('/accounts', z.array(accountOptionSchema)),
  });
};
