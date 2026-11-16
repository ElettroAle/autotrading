import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import type { EmergencyScope } from '../types/emergency-scope';
import { scopeQuery } from '../utils/emergency-question';

const outcomeSchema = z.object({
  flow_id: z.string(),
  flow_name: z.string(),
  closed: z.array(z.string()),
  left_open: z.array(z.object({ asset: z.string(), reason: z.string() })),
  failure: z.string().nullable(),
  remark: z.string().nullable(),
});

const closingSchema = z.object({ flows: z.array(outcomeSchema) });

export type FlowEmergencyOutcome = z.infer<typeof outcomeSchema>;
export type EmergencyClosing = z.infer<typeof closingSchema>;

/**
 * Closes every position of the flows of the scope and pauses them (R3.2.3). Flows, positions and accounts of any page
 * may have changed, so every read of the dashboard is read again.
 */
export const useCloseInEmergency = (scope: EmergencyScope) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      readData(
        await api.POST('/flows/emergency-closings', { body: scopeQuery(scope) }),
        closingSchema,
      ),
    onSettled: () => queryClient.invalidateQueries(),
  });
};
