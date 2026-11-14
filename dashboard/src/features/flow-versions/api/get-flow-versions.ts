import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const versionSchema = z.object({ version: z.number(), created_at: z.string() });

export type Version = z.infer<typeof versionSchema>;

/** The configuration versions of the flow with when each was saved, newest first (R2.3.5, ADR 0133). */
export const useFlowVersions = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['flows', flowId, 'versions'],
    queryFn: () => api.get(`/flows/${encodeURIComponent(flowId)}/versions`, z.array(versionSchema)),
  });
};
