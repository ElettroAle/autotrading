import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { SOURCE_CREDENTIALS_QUERY_KEY } from './get-source-credentials';

type SourceCredentialsExpiry = { readonly adapter: string; readonly expiresOn: string | null };

/** The day the credentials of the adapter expire, given by the user; none forgets it (R6.2.2). */
export const useSetSourceCredentialsExpiry = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ adapter, expiresOn }: SourceCredentialsExpiry) =>
      readDone(
        await api.PUT('/source-credentials/{adapter}/expiry', {
          params: { path: { adapter } },
          body: { expires_on: expiresOn },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SOURCE_CREDENTIALS_QUERY_KEY }),
  });
};
