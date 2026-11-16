import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const flowAssetsSchema = z.array(z.object({ id: z.string(), assets: z.array(z.string()) }));

/** The assets of the configuration of the flow in force, the choices of the filter by asset (R6.4.4). */
export const useFlowAssets = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    // Its own key under the flows: the list elsewhere keeps other fields of each flow, and both refresh together.
    ...pageDataQuery('flows', 'assets'),
    queryFn: async () => readData(await api.GET('/flows'), flowAssetsSchema),
    select: (flows) => flows.find((flow) => flow.id === flowId)?.assets ?? [],
  });
};
