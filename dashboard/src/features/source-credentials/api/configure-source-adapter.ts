import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';
import { dayOrNothing } from '@/utils/format-day';

import { SOURCE_CREDENTIALS_QUERY_KEY } from './get-source-credentials';

// The values of the fields the adapter declares: the API names the missing one and seals the secrets (R4.1.2).
// The day the credentials expire, when the user knows it (R6.2.2).
export const sourceCredentialsInputSchema = z.object({
  values: z.record(z.string(), z.string()),
  expires_on: z.string().optional(),
});

export type SourceCredentialsInput = z.infer<typeof sourceCredentialsInputSchema>;

type SourceAdapterConfiguration = SourceCredentialsInput & { readonly adapter: string };

/** Saves the credentials of the adapter, or replaces them; nothing stays in the cache (ADR 0130). */
export const useConfigureSourceAdapter = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ adapter, values, expires_on }: SourceAdapterConfiguration) =>
      readDone(
        await api.PUT('/source-credentials/{adapter}', {
          params: { path: { adapter } },
          body: { values, expires_on: dayOrNothing(expires_on) },
        }),
      ),
    gcTime: 0,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SOURCE_CREDENTIALS_QUERY_KEY }),
  });
};
