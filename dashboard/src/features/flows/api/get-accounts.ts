import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const accountsSchema = z.array(
  z.object({ id: z.string(), name: z.string(), network: z.string(), network_name: z.string() }),
);

export type Account = z.infer<typeof accountsSchema>[number];

/**
 * The accounts of the tenant a flow can run on, with the network each trades on (Bug 277). A key of their own, under
 * the accounts every change of an account rereads: the cache keeps the accounts already passed through this schema
 * (Bug 437).
 */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts', 'flows'),
    queryFn: async () => readData(await api.GET('/accounts'), accountsSchema),
  });
};
