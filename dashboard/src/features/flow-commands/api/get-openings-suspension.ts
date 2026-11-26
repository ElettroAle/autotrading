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
  // The sides whose reopenings stop after consecutive losses, each with the text of the API (R5.5.2, ADR
  // blocco-delle-riaperture-nella-dashboard).
  reopening_blocks: z.array(z.object({ text: z.string() })),
});

type OpeningsState = z.infer<typeof openingsSuspensionSchema>;

// One reading of the state for the suspension and the blocks: what may stop the openings of the flow now.
const useOpeningsState = <T>(flowId: string, select: (state: OpeningsState) => T) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flow-state', flowId, 'openings-suspension'),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/state', { params: { path: { flow_id: flowId } } }),
        openingsSuspensionSchema,
      ),
    select,
  });
};

/** The suspension of the openings of the flow in force now, from its state; null when it may open (R3.2.2, R3.3.2). */
export const useOpeningsSuspension = (flowId: string) =>
  useOpeningsState(flowId, (state) => state.openings_suspension);

/** The texts of the blocks of the reopenings in force now, from the same state; none without the limit (R5.5.2). */
export const useReopeningBlocks = (flowId: string) =>
  useOpeningsState(flowId, (state) => state.reopening_blocks.map((block) => block.text));
