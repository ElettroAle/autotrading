import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

export const amountSchema = z.object({ amount: z.string(), currency: z.string() });

const accountStateSchema = z.object({ balance: amountSchema });

/** The balance of one account read now from the exchange (R0.2.2): a query of its own, so it fails alone. */
export const useAccountBalance = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts', accountId, 'state'),
    queryFn: async () =>
      readData(
        await api.GET('/accounts/{account_id}/state', {
          params: { path: { account_id: accountId } },
        }),
        accountStateSchema,
      ),
    select: (state) => state.balance,
  });
};
