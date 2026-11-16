import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

// The secret credentials are only declared present, never returned (R0.2.3); the public fields the exchange declares,
// as the account address, are shown by name (Bug 401); the balance is read apart (ADR 0126).
export const accountSchema = z.object({
  id: z.string(),
  name: z.string(),
  exchange: z.string(),
  has_credentials: z.boolean(),
  public_fields: z.record(z.string(), z.string()),
  network: z.string(),
  network_name: z.string(),
  allocated_capital: z.string(),
  currency: z.string(),
});

export type Account = z.infer<typeof accountSchema>;

// Every reading of the accounts starts with this key: a change of an account invalidates them all (Bug 437).
export const ACCOUNTS_QUERY_KEY = ['accounts'] as const;

/** The accounts of the tenant of the user, with network and allocated capital, never the balance (ADR 0126). */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...ACCOUNTS_QUERY_KEY),
    queryFn: async () => readData(await api.GET('/accounts'), z.array(accountSchema)),
  });
};
