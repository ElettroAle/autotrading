import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';
import { assetMemorySchema } from '@/types/flow-memory';

const flowMemorySchema = z.object({ active: z.boolean(), assets: z.array(assetMemorySchema) });

/** What the agent of the flow would receive if its cycle started now; nothing with the memory off (R5.3.4). */
export const useFlowMemory = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-memory', flowId),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/memory', { params: { path: { flow_id: flowId } } }),
        flowMemorySchema,
      ),
  });
};
