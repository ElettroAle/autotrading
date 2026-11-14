import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const differenceSchema = z.object({ part: z.string(), before: z.string(), after: z.string() });

export type Difference = z.infer<typeof differenceSchema>;

/** What changed from one version to the other: the comparison is the one of the API, never the browser's (ADR 0133). */
export const useVersionDifferences = (flowId: string, first: number, second: number) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['flows', flowId, 'versions', first, 'differences', second],
    queryFn: () =>
      api.get(
        `/flows/${encodeURIComponent(flowId)}/versions/${first}/differences/${second}`,
        z.array(differenceSchema),
      ),
  });
};
