import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const identitySchema = z.object({ user_id: z.string(), tenant_id: z.string() });

/** Who the API recognises: at the first access the API creates the tenant of the user (R0.1.2). */
export const useIdentity = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['identity'],
    queryFn: async () => readData(await api.GET('/me'), identitySchema),
  });
};
