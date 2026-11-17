import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import {
  NOTIFICATION_CHANNELS_QUERY_KEY,
  type NotificationChannel,
  type NotificationEvent,
} from './get-notification-channels';

export type ChannelChoice = {
  readonly event: NotificationEvent;
  readonly channel: NotificationChannel;
};

/** Chooses the channel of a type of event for all the flows: it counts from the next notification (R3.5.3). */
export const useChooseNotificationChannel = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (choice: ChannelChoice) =>
      readDone(await api.PUT('/notifications/channels', { body: choice })),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_CHANNELS_QUERY_KEY }),
  });
};
