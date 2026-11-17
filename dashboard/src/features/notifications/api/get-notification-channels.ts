import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import type { components } from '@/lib/api-schema';
import { pageDataQuery } from '@/lib/react-query';

/** A channel by the name the API gives it: the list comes from the API, so a new channel shows by itself. */
export type NotificationChannel = components['schemas']['ChannelStateResponse']['channel'];

const channelSchema = z.custom<NotificationChannel>((value) => typeof value === 'string');

/** A type of event by the name the API gives it: the list comes from the API, so a new type shows by itself. */
export type NotificationEvent = components['schemas']['NotificationEvent'];

const eventSchema = z.custom<NotificationEvent>((value) => typeof value === 'string');

const eventChannelSchema = z.object({
  event: eventSchema,
  channels: z.array(channelSchema),
  of_flow: z.boolean(),
  warnings: z.array(z.string()),
});

const channelStateSchema = z.object({
  channel: channelSchema,
  configured: z.boolean(),
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
  channels: z.array(channelStateSchema),
  warnings: z.array(z.string()),
});

export type EventChannel = z.infer<typeof eventChannelSchema>;

export type ChannelState = z.infer<typeof channelStateSchema>;

export type NotificationChannels = z.infer<typeof notificationChannelsSchema>;

export const NOTIFICATION_CHANNELS_QUERY_KEY = ['notification-channels'] as const;

/**
 * The channels of every type of event, the exceptions of every flow, every channel of the platform with its state, the
 * warnings of a chosen channel not linked and those of every channel that cannot be reached, as the API computes them
 * (R3.5.3, R3.5.5, ADR canali-delle-notifiche-come-insieme).
 */
export const useNotificationChannels = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...NOTIFICATION_CHANNELS_QUERY_KEY),
    queryFn: async () =>
      readData(await api.GET('/notifications/channels'), notificationChannelsSchema),
  });
};
