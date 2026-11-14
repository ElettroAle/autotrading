import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const accountSchema = z.object({ id: z.string(), name: z.string(), exchange: z.string() });

export type Account = z.infer<typeof accountSchema>;

/** The accounts of the tenant a flow can trade on (R0.2.1). */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounts', z.array(accountSchema)),
  });
};
