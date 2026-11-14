import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const accountsSchema = z.array(z.object({ id: z.string(), name: z.string() }));

export type Account = z.infer<typeof accountsSchema>[number];

/** The accounts of the tenant a flow can run on. */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts'),
    queryFn: async () => readData(await api.GET('/accounts'), accountsSchema),
  });
};
