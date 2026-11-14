import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

/** The assets a flow can trade now on the exchange of the installation, by name, as the API lists them (ADR 0147). */
export const useTradableAssets = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['assets'],
    queryFn: async () => readData(await api.GET('/assets'), z.array(z.string())),
  });
};
