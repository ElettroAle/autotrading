import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

// Why the openings are suspended is the API's: the page shows its reason (ADR stato-della-riconciliazione-nella-dashboard).
const openingsSuspensionSchema = z.object({ openings_suspended: z.string().nullable() });

/** Why the openings of the flow are suspended, from its state read now; null when they are not (R3.3.2). */
export const useOpeningsSuspension = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-state', flowId, 'openings-suspension'),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', { params: { path: { flow_id: flowId } } }),
        openingsSuspensionSchema,
      ),
    select: (state) => state.openings_suspended,
  });
};
