import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';

import { NOTIFICATION_EMAIL_QUERY_KEY } from './get-notification-email';

// The form of the address is judged by the API alone (ADR indirizzo-email-nelle-impostazioni-delle-notifiche).
export const notificationEmailInputSchema = z.object({ address: z.string() });

export type NotificationEmailInput = z.infer<typeof notificationEmailInputSchema>;

/** Indicates or changes the address of the notifications by email: it counts at once (R3.5.2). */
export const useSetNotificationEmail = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: NotificationEmailInput) =>
      readDone(await api.PUT('/notifications/email', { body: input })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_EMAIL_QUERY_KEY }),
  });
};
