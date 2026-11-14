import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import { amountSchema } from './get-account-state';

/** The capital of one account still free for new flows, as the API computes it (R1.1.7). */
export const useFreeCapital = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['accounts', accountId, 'free-capital'],
    queryFn: () => api.get(`/accounts/${encodeURIComponent(accountId)}/free-capital`, amountSchema),
  });
};
