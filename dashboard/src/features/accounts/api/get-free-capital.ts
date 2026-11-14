import { useQuery } from '@tanstack/react-query';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { amountSchema } from './get-account-state';

/** The capital of one account still free for new flows, as the API computes it (R1.1.7). */
export const useFreeCapital = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts', accountId, 'free-capital'),
    queryFn: async () =>
      readData(
        await api.GET('/accounts/{account_id}/free-capital', {
          params: { path: { account_id: accountId } },
        }),
        amountSchema,
      ),
  });
};
