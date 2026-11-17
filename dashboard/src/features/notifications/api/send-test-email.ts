import { useMutation } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

/** The test email to the address of the notifications, by the road of the real ones (R3.5.2). */
export const useSendTestEmail = () => {
  const api = useApiClient();
  return useMutation({
    mutationFn: async () => readDone(await api.POST('/notifications/email/test')),
  });
};
