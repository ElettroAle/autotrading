import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import {
  NOTIFICATION_CHANNELS_QUERY_KEY,
  type NotificationEvent,
} from './get-notification-channels';

export type FlowEvent = { readonly flowId: string; readonly event: NotificationEvent };

/** Takes away the exception of a flow: the flow follows the general choice again (R3.5.3). */
export const useRemoveFlowChannelException = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ flowId, event }: FlowEvent) =>
      readDone(
        await api.DELETE('/notifications/channels/flows/{flow_id}/{event}', {
          params: { path: { flow_id: flowId, event } },
        }),
      ),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_CHANNELS_QUERY_KEY }),
  });
};
