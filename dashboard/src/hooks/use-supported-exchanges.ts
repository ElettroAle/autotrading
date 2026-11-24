import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const declaredFieldSchema = z.object({ name: z.string(), label: z.string(), secret: z.boolean() });

const supportedExchangesSchema = z.array(
  z.object({
    name: z.string(),
    network: z.string(),
    network_name: z.string(),
    fields: z.array(declaredFieldSchema),
    // False where the exchange reads the expiry of the credentials (R6.2.2).
    expiry_editable: z.boolean(),
    // True where the exchange holds a virtual balance, which the registration asks instead of funds (R6.3.2).
    virtual_balance: z.boolean(),
  }),
);

export type SupportedExchange = z.infer<typeof supportedExchangesSchema>[number];

/**
 * The exchanges an account can be registered on, as the API lists them (ADR 0152), each with the network it trades
 * on (ADR 0157), the fields its credentials ask (R2.3.9, ADR 0158), whether the user gives their expiry (R6.2.2) and
 * whether it holds a virtual balance (R6.3.2).
 */
export const useSupportedExchanges = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['exchanges'],
    queryFn: async () => readData(await api.GET('/exchanges'), supportedExchangesSchema),
  });
};
