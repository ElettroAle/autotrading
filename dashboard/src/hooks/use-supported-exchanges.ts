import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const supportedExchangesSchema = z.array(z.object({ name: z.string(), network: z.string() }));

export type SupportedExchange = z.infer<typeof supportedExchangesSchema>[number];

/**
 * The exchanges an account can be registered on, as the API lists them (ADR 0152), each with the network it trades
 * on (ADR 0157).
 */
export const useSupportedExchanges = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['exchanges'],
    queryFn: async () => readData(await api.GET('/exchanges'), supportedExchangesSchema),
  });
};
