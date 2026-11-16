import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

// One suspension whatever its cause, decided by the API: the page shows its reason and offers the resume only when the
// API says the user may (ADR perdita-massima-nella-dashboard, stato-della-riconciliazione-nella-dashboard).
const openingsSuspensionSchema = z.object({
  openings_suspension: z
    .object({
      reason: z.string(),
      suspended_at: z.string(),
      cause: z.enum(['perdita_massima', 'riconciliazione']),
      resumable: z.boolean(),
    })
    .nullable(),
});

/** The suspension of the openings of the flow in force now, from its state; null when it may open (R3.2.2, R3.3.2). */
export const useOpeningsSuspension = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-state', flowId, 'openings-suspension'),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', { params: { path: { flow_id: flowId } } }),
        openingsSuspensionSchema,
      ),
    select: (state) => state.openings_suspension,
  });
};
