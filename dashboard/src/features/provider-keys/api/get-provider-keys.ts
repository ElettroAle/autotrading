import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

// Only the provider and the instant of the last registration or replacement: never the key (R1.4.1, ADR 0130).
export const providerKeySchema = z.object({ provider: z.string(), registered_at: z.string() });

export type ProviderKey = z.infer<typeof providerKeySchema>;

export const PROVIDER_KEYS_QUERY_KEY = ['provider-keys'] as const;

/** The providers the tenant of the user has a key for. */
export const useProviderKeys = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: PROVIDER_KEYS_QUERY_KEY,
    queryFn: () => api.get('/provider-keys', z.array(providerKeySchema)),
  });
};
