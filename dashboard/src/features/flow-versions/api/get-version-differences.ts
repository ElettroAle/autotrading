import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const differenceSchema = z.object({ part: z.string(), before: z.string(), after: z.string() });

export type Difference = z.infer<typeof differenceSchema>;

/** What changed from one version to the other: the comparison is the one of the API, never the browser's (ADR 0133). */
export const useVersionDifferences = (flowId: string, first: number, second: number) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'versions', first, 'differences', second),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/versions/{first}/differences/{second}', {
          params: { path: { flow_id: flowId, first, second } },
        }),
        z.array(differenceSchema),
      ),
  });
};
