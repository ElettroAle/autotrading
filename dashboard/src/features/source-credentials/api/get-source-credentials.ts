import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';
import { keyExpiryFields } from '@/types/key-expiry';

// An adapter of a source that needs configuration, as the API answers it: its fields, whether the tenant configured
// it, the values that are not secret and the expiry as of today; never a secret (R4.1.2, R6.2.2).
const sourceCredentialsSchema = z.object({
  adapter: z.string(),
  sources: z.array(z.string()),
  configuration_fields: z.array(
    z.object({ name: z.string(), label: z.string(), secret: z.boolean() }),
  ),
  configured: z.boolean(),
  public_values: z.record(z.string(), z.string()),
  registered_at: z.string().nullable(),
  rejected: z.boolean(),
  ...keyExpiryFields,
});

export type SourceCredentials = z.infer<typeof sourceCredentialsSchema>;

export const SOURCE_CREDENTIALS_QUERY_KEY = ['source-credentials'] as const;

/** The adapters of the sources that need configuration, with the credentials the tenant gave them. */
export const useSourceCredentials = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...SOURCE_CREDENTIALS_QUERY_KEY),
    queryFn: async () =>
      readData(await api.GET('/source-credentials'), z.array(sourceCredentialsSchema)),
  });
};
