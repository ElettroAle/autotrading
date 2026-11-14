import { useMutation } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

/** The test notification of R1.8.1, to the chat linked to the tenant, by the road of the real ones (ADR 0134). */
export const useSendTestNotification = () => {
  const api = useApiClient();
  return useMutation({
    mutationFn: async () => readDone(await api.POST('/telegram/test-notification')),
  });
};
