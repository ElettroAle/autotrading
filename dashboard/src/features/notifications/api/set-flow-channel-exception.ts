import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import {
  NOTIFICATION_CHANNELS_QUERY_KEY,
  type NotificationChannel,
  type NotificationEvent,
} from './get-notification-channels';

export type FlowChannelException = {
  readonly flowId: string;
  readonly event: NotificationEvent;
  readonly channel: NotificationChannel;
};

/** Gives a flow a channel of its own for a type of event of the flow (R3.5.3). */
export const useSetFlowChannelException = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ flowId, event, channel }: FlowChannelException) =>
      readDone(
        await api.PUT('/notifications/channels/flows/{flow_id}/{event}', {
          params: { path: { flow_id: flowId, event } },
          body: { channel },
        }),
      ),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_CHANNELS_QUERY_KEY }),
  });
};
