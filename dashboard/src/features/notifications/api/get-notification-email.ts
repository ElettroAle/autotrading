import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const notificationEmailSchema = z.object({
  address: z.string().nullable(),
  warning: z.string().nullable(),
});

export type NotificationEmail = z.infer<typeof notificationEmailSchema>;

export const NOTIFICATION_EMAIL_QUERY_KEY = ['notification-email'] as const;

/** The address of the notifications by email, and the warning of the API when no email leaves (R3.5.2). */
export const useNotificationEmail = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...NOTIFICATION_EMAIL_QUERY_KEY),
    queryFn: async () => readData(await api.GET('/notifications/email'), notificationEmailSchema),
  });
};
