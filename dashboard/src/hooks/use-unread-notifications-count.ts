import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { NOTIFICATIONS_QUERY_KEY } from './use-notification-inbox';

const inboxSummarySchema = z.object({ unread_count: z.number() });

/**
 * How many notifications of the user are unread, for the bell of every page: page data, reread with the page (R2.1.2,
 * ADR campanello-delle-notifiche-nella-dashboard). Under the key of the notifications, so reading one reads it again.
 */
export const useUnreadNotificationsCount = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...NOTIFICATIONS_QUERY_KEY, 'summary'),
    queryFn: async () =>
      readData(await api.GET('/notifications/inbox/summary'), inboxSummarySchema),
    select: (summary) => summary.unread_count,
  });
};
