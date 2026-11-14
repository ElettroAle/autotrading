import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const accountSchema = z.object({
  id: z.string(),
  name: z.string(),
  network: z.string(),
  allocated_capital: z.string(),
  currency: z.string(),
});

export type Account = z.infer<typeof accountSchema>;

const accountsSchema = z.array(accountSchema);

/** The accounts of the tenant of the user, with network and allocated capital, never the balance (ADR 0126). */
export const useAccounts = () => {
  const api = useApiClient();
  return useQuery({ queryKey: ['accounts'], queryFn: () => api.get('/accounts', accountsSchema) });
};
