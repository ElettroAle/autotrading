import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const lastDecisionSchema = z
  .object({
    planned_at: z.string(),
    decisions: z.array(
      z.object({
        asset: z.string(),
        action: z.string(),
        direction: z.string().nullable(),
        confidence: z.number().nullable(),
        reasoning: z.string(),
      }),
    ),
  })
  .nullable();

export type LastDecision = NonNullable<z.infer<typeof lastDecisionSchema>>;

export type Decision = LastDecision['decisions'][number];

/**
 * The last decision of the agent in the flow, null before the first: the key has no period, since the decision does
 * not depend on it (ADR riquadro-dell-ultima-decisione-nella-panoramica).
 */
export const useLastDecision = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('last-decision', flowId),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/decisions/latest', {
          params: { path: { flow_id: flowId } },
        }),
        lastDecisionSchema,
      ),
  });
};
