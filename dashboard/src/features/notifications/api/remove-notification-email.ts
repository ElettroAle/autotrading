import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

import { NOTIFICATION_EMAIL_QUERY_KEY } from './get-notification-email';

/** Removes the address of the notifications by email: they stop going there, the flows go on (R3.5.2). */
export const useRemoveNotificationEmail = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => readDone(await api.DELETE('/notifications/email')),
    onSettled: () => queryClient.invalidateQueries({ queryKey: NOTIFICATION_EMAIL_QUERY_KEY }),
  });
};
