import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const accountsSchema = z.array(z.object({ id: z.string(), name: z.string() }));

export type Account = z.infer<typeof accountsSchema>[number];

/** The accounts of the tenant a flow can run on. */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({ queryKey: ['accounts'], queryFn: () => api.get('/accounts', accountsSchema) });
};
