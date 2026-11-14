import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const linkCodeSchema = z.object({
  code: z.string(),
  expires_at: z.string(),
  link: z.string().nullable(),
});

export type LinkCode = z.infer<typeof linkCodeSchema>;

/** A one-time code to send to the bot from the chat to link, with the link of the bot when it is active (R1.8.1). */
export const useRequestLinkCode = () => {
  const api = useApiClient();
  return useMutation({ mutationFn: () => api.post('/telegram/link-code', linkCodeSchema) });
};
