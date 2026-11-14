import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const versionSchema = z.object({ version: z.number(), created_at: z.string() });

export type Version = z.infer<typeof versionSchema>;

/** The configuration versions of the flow with when each was saved, newest first (R2.3.5, ADR 0133). */
export const useFlowVersions = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'versions'),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/versions', { params: { path: { flow_id: flowId } } }),
        z.array(versionSchema),
      ),
  });
};
