import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { MAIL_SERVER_QUERY_KEY } from './get-mail-server';
import { NOTIFICATION_CHANNELS_QUERY_KEY } from './get-notification-channels';
import { NOTIFICATION_EMAIL_QUERY_KEY } from './get-notification-email';

/** Removes the mail server of the user: no email leaves until another is saved (R3.5.5). */
export const useRemoveMailServer = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => readDone(await api.DELETE('/notifications/mail-server')),
    onSettled: () =>
      Promise.all(
        [MAIL_SERVER_QUERY_KEY, NOTIFICATION_EMAIL_QUERY_KEY, NOTIFICATION_CHANNELS_QUERY_KEY].map(
          (queryKey) => queryClient.invalidateQueries({ queryKey }),
        ),
      ),
  });
};
