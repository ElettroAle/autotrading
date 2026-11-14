import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

/** The assets a flow can trade now on the exchange of the installation, by name, as the API lists them (ADR 0147). */
export const useTradableAssets = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['assets'],
    queryFn: () => api.get('/assets', z.array(z.string())),
  });
};
