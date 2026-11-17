import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import {
  NOTIFICATION_CHANNELS_QUERY_KEY,
  type NotificationChannel,
  type NotificationEvent,
} from './get-notification-channels';

export type ChannelChoice = {
  readonly event: NotificationEvent;
  readonly channels: readonly NotificationChannel[];
};

/**
 * Chooses the channels of a type of event for all the flows, none for no notification: it counts from the next
 * notification (R3.5.3).
 */
export const useChooseNotificationChannel = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (choice: ChannelChoice) =>
      readDone(
        await api.PUT('/notifications/channels', {
          body: { event: choice.event, channels: [...choice.channels] },
        }),
      ),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_CHANNELS_QUERY_KEY }),
  });
};
