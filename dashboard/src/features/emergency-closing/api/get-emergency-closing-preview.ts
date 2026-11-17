import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import type { EmergencyScope } from '../types/emergency-scope';
import { scopeQuery } from '../utils/emergency-question';

const previewSchema = z.object({ flows: z.number(), positions: z.number() });

export type EmergencyClosingPreview = z.infer<typeof previewSchema>;

/**
 * What the emergency closing would touch now, read from the API when the user asks for it: the dashboard counts
 * nothing (ADR chiusura-di-emergenza-nella-dashboard). Never kept: the positions change while the user decides.
 */
export const useEmergencyClosingPreview = (scope: EmergencyScope, enabled: boolean) => {
  const api = useApiClient();
  const query = scopeQuery(scope);
  return useQuery({
    queryKey: ['emergency-closing-preview', query.flow_id ?? null, query.account_id ?? null],
    queryFn: async () =>
      readData(
        await api.GET('/flows/emergency-closings/preview', { params: { query } }),
        previewSchema,
      ),
    enabled,
    staleTime: 0,
    gcTime: 0,
  });
};
