import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, readDone, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

/** The key of every read of the bell: reading a notification invalidates them all. */
export const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const;

const targetSchema = z.object({
  kind: z.enum(['flow', 'open_position', 'closed_position', 'alert']),
  label: z.string(),
  flow_id: z.string().nullable(),
  asset: z.string().nullable(),
  closed_at: z.string().nullable(),
  alert_id: z.string().nullable(),
});

const inboxNotificationSchema = z.object({
  id: z.string(),
  icon: z.string(),
  title: z.string(),
  text: z.string(),
  notified_at: z.string(),
  read_at: z.string().nullable(),
  targets: z.array(targetSchema),
});

export type InboxNotification = z.infer<typeof inboxNotificationSchema>;

const inboxPageSchema = z.object({
  items: z.array(inboxNotificationSchema),
  next: z.string().nullable(),
});

/**
 * The notifications of the bell, newest first, in the pages of the API, read while the bell is open (R6.2.1, ADR
 * 0074): page data, reread with the page.
 */
export const useInboxNotifications = (open: boolean) => {
  const api = useApiClient();
  return useInfiniteQuery({
    ...pageDataQuery(...NOTIFICATIONS_QUERY_KEY, 'list'),
    queryFn: async ({ pageParam }) =>
      readData(
        await api.GET('/notifications/inbox', {
          params: { query: { cursor: pageParam ?? undefined } },
        }),
        inboxPageSchema,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: open,
  });
};

/** One notification read: the bell and its number read again. */
export const useMarkNotificationRead = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) =>
      readDone(
        await api.POST('/notifications/inbox/{notification_id}/read', {
          params: { path: { notification_id: notificationId } },
        }),
      ),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY }),
  });
};

/** Every notification read at once: the bell and its number read again. */
export const useMarkAllNotificationsRead = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => readDone(await api.POST('/notifications/inbox/read')),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY }),
  });
};
