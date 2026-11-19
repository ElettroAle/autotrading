import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { PROVIDER_KEYS_QUERY_KEY } from './get-provider-keys';

const keyFieldSchema = z.object({ name: z.string(), label: z.string(), secret: z.boolean() });

const providerSchema = z.object({
  name: z.string(),
  key_registered: z.boolean(),
  key_fields: z.array(keyFieldSchema),
  // False where a gateway reads the expiry of the keys of the provider (R6.2.2).
  expiry_editable: z.boolean(),
});

/**
 * A provider of the catalog of the models, with whether the user registered its key (R1.4.1) and the fields its key
 * asks (R2.3.9, ADR 0159).
 */
export type ModelProvider = z.infer<typeof providerSchema>;

const catalogProvidersSchema = z.object({ providers: z.array(providerSchema) });

/**
 * The providers of the catalog of the models (R1.4.2, ADR 0153). The key sits under the one of the keys: registering
 * or removing a key rereads which providers have it.
 */
export const useModelProviders = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: [...PROVIDER_KEYS_QUERY_KEY, 'catalog'],
    queryFn: async () =>
      (await readData(await api.GET('/models'), catalogProvidersSchema)).providers,
  });
};
