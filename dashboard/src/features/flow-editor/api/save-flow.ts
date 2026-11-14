import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import type { CreationRequest, FlowChanges } from '../utils/flow-form';

import { flowSchema, type Flow } from './get-flow';

const FLOWS = ['flows'];

/** A new stopped flow at its first version, or the refusal with the setting it concerns (R1.1.1). */
export const useCreateFlow = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreationRequest) => api.write('POST', '/flows', request, flowSchema),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FLOWS }),
  });
};

/**
 * Only the changed settings, as the next configuration version (R1.1.3); the capital through its own request, with
 * its history (R1.1.7, ADR 0131). The answer is the flow at the last version saved.
 */
export const useModifyFlow = (flow: Flow) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const path = `/flows/${encodeURIComponent(flow.id)}`;
  return useMutation({
    mutationFn: async ({ settings, capital }: FlowChanges): Promise<Flow> => {
      const modified =
        Object.keys(settings).length === 0
          ? flow
          : await api.write('PATCH', path, settings, flowSchema);
      return capital === undefined
        ? modified
        : api.write('PUT', `${path}/allocated-capital`, { allocated_capital: capital }, flowSchema);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: FLOWS }),
  });
};
