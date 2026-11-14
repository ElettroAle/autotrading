import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

export const amountSchema = z.object({ amount: z.string(), currency: z.string() });

const accountStateSchema = z.object({ balance: amountSchema });

/** The balance of one account read now from the exchange (R0.2.2): a query of its own, so it fails alone. */
export const useAccountBalance = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['accounts', accountId, 'state'],
    queryFn: () => api.get(`/accounts/${encodeURIComponent(accountId)}/state`, accountStateSchema),
    select: (state) => state.balance,
  });
};
