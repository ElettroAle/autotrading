import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import type { components } from '@/lib/api-schema';
import { pageDataQuery } from '@/lib/react-query';

export const CHANNELS = ['Telegram', 'email', 'entrambi', 'nessuno'] as const;

const channelSchema = z.enum(CHANNELS);

/** A type of event by the name the API gives it: the list comes from the API, so a new type shows by itself. */
export type NotificationEvent = components['schemas']['NotificationEvent'];

const eventSchema = z.custom<NotificationEvent>((value) => typeof value === 'string');

const eventChannelSchema = z.object({
  event: eventSchema,
  channel: channelSchema,
  of_flow: z.boolean(),
  warnings: z.array(z.string()),
});

const notificationChannelsSchema = z.object({
  events: z.array(eventChannelSchema),
  flows: z.array(
    z.object({
      flow_id: z.string(),
      name: z.string(),
      exceptions: z.array(eventChannelSchema),
    }),
  ),
  warnings: z.array(z.string()),
});

export type NotificationChannel = z.infer<typeof channelSchema>;

export type EventChannel = z.infer<typeof eventChannelSchema>;

export type NotificationChannels = z.infer<typeof notificationChannelsSchema>;

export const NOTIFICATION_CHANNELS_QUERY_KEY = ['notification-channels'] as const;

/**
 * The channel of every type of event, the exceptions of every flow, the warnings of a channel not linked and those of
 * every channel that cannot be reached, as the API computes them (R3.5.3, R3.5.5).
 */
export const useNotificationChannels = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...NOTIFICATION_CHANNELS_QUERY_KEY),
    queryFn: async () =>
      readData(await api.GET('/notifications/channels'), notificationChannelsSchema),
  });
};
