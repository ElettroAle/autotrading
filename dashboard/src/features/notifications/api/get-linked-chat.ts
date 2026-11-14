import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

const linkedChatSchema = z.object({ linked: z.boolean(), chat_id: z.number().nullable() });

export type LinkedChat = z.infer<typeof linkedChatSchema>;

export const LINKED_CHAT_QUERY_KEY = ['telegram-chat'] as const;

/** The chat linked to the tenant of the user, the only one its notifications go to (R1.8.1). */
export const useLinkedChat = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: LINKED_CHAT_QUERY_KEY,
    queryFn: () => api.get('/telegram/chat', linkedChatSchema),
  });
};
