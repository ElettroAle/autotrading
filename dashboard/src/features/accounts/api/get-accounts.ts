import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

// The credentials are only declared present, never returned (R0.2.3); the balance is read apart (ADR 0126).
export const accountSchema = z.object({
  id: z.string(),
  name: z.string(),
  exchange: z.string(),
  has_credentials: z.boolean(),
  network: z.string(),
  allocated_capital: z.string(),
  currency: z.string(),
});

export type Account = z.infer<typeof accountSchema>;

export const ACCOUNTS_QUERY_KEY = ['accounts'] as const;

/** The accounts of the tenant of the user, with network and allocated capital, never the balance (ADR 0126). */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...ACCOUNTS_QUERY_KEY),
    queryFn: async () => readData(await api.GET('/accounts'), z.array(accountSchema)),
  });
};
