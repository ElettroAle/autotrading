import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';
import { keyExpiryFields } from '@/types/key-expiry';

// Only the provider and the instant of the last registration or replacement: never the key (R1.4.1, ADR 0130).
export const providerKeySchema = z.object({ provider: z.string(), registered_at: z.string() });

// On the page of the keys each key carries its expiry as the API reads it today (R6.2.2).
const providerKeySummarySchema = providerKeySchema.extend(keyExpiryFields);

export type ProviderKey = z.infer<typeof providerKeySummarySchema>;

export const PROVIDER_KEYS_QUERY_KEY = ['provider-keys'] as const;

/** The providers the tenant of the user has a key for. */
export const useProviderKeys = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...PROVIDER_KEYS_QUERY_KEY),
    queryFn: async () =>
      readData(await api.GET('/provider-keys'), z.array(providerKeySummarySchema)),
  });
};
