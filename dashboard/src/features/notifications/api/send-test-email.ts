import { useMutation } from '@tanstack/react-query';

import { readDone, useApiClient } from '@/lib/api-client';

/** The test email, sent at once from the mail server of the user: a refusal of the server is the answer (R3.5.5). */
export const useSendTestEmail = () => {
  const api = useApiClient();
  return useMutation({
    mutationFn: async () => readDone(await api.POST('/notifications/email/test')),
  });
};
