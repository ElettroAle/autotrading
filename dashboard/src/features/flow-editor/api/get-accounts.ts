import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const accountSchema = z.object({ id: z.string(), name: z.string(), exchange: z.string() });

export type Account = z.infer<typeof accountSchema>;

/**
 * The accounts of the tenant a flow can trade on (R0.2.1). A key of their own, under the accounts every change of an
 * account rereads: the cache keeps the accounts already passed through this schema (Bug 437).
 */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['accounts', 'flow-editor'],
    queryFn: async () => readData(await api.GET('/accounts'), z.array(accountSchema)),
  });
};
