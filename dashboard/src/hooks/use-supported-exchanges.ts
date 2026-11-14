import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

/** The exchanges an account can be registered on, by name, as the API lists them (ADR 0152). */
export const useSupportedExchanges = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['exchanges'],
    queryFn: async () => readData(await api.GET('/exchanges'), z.array(z.string())),
  });
};
