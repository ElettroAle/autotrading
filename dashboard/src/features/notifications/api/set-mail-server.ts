import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readDone, useApiClient } from '@/lib/api-client';

import { MAIL_SERVER_QUERY_KEY, securitySchema } from './get-mail-server';
import { NOTIFICATION_CHANNELS_QUERY_KEY } from './get-notification-channels';
import { NOTIFICATION_EMAIL_QUERY_KEY } from './get-notification-email';

// The form of the values is judged by the API alone: the port is written as text and sent as a number (ADR
// pagina-notifiche-a-schede).
export const mailServerInputSchema = z.object({
  host: z.string(),
  port: z.string(),
  security: securitySchema,
  username: z.string(),
  password: z.string(),
  sender: z.string(),
});

export type MailServerInput = z.infer<typeof mailServerInputSchema>;

/** Saves the mail server of the user: an empty password keeps the saved one (R3.5.5). */
export const useSetMailServer = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ port, password, ...server }: MailServerInput) =>
      readDone(
        await api.PUT('/notifications/mail-server', {
          body: { ...server, port: Number(port), password: password === '' ? null : password },
        }),
      ),
    onSuccess: () =>
      Promise.all(
        [MAIL_SERVER_QUERY_KEY, NOTIFICATION_EMAIL_QUERY_KEY, NOTIFICATION_CHANNELS_QUERY_KEY].map(
          (queryKey) => queryClient.invalidateQueries({ queryKey }),
        ),
      ),
  });
};
