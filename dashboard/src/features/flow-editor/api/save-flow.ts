import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readData, useApiClient } from '@/lib/api-client';
import type { components } from '@/lib/api-schema';

import type { CreationRequest, FlowChanges } from '../utils/flow-form';

import { flowSchema, type Flow } from './get-flow';

const FLOWS = ['flows'];

// A blank capital is left out on purpose, although the API requires it: the API then names it as missing beside its
// field, as for every other rule (ADR 0130).
type CreationBody = components['schemas']['FlowCreationRequest'];

/** A new stopped flow at its first version, or the refusal with the setting it concerns (R1.1.1). */
export const useCreateFlow = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: CreationRequest) =>
      readData(await api.POST('/flows', { body: request as CreationBody }), flowSchema),
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
  const params = { path: { flow_id: flow.id } };
  return useMutation({
    mutationFn: async ({ settings, capital }: FlowChanges): Promise<Flow> => {
      const modified =
        Object.keys(settings).length === 0
          ? flow
          : readData(await api.PATCH('/flows/{flow_id}', { params, body: settings }), flowSchema);
      return capital === undefined
        ? modified
        : readData(
            await api.PUT('/flows/{flow_id}/allocated-capital', {
              params,
              body: { allocated_capital: capital },
            }),
            flowSchema,
          );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: FLOWS }),
  });
};
