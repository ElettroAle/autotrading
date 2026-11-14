import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/lib/api-client';

import { LINKED_CHAT_QUERY_KEY } from './get-linked-chat';

/** Unlinks the chat of the tenant: its notifications stop, its flows go on (R1.8.1). */
export const useUnlinkChat = () => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.send('DELETE', '/telegram/chat'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: LINKED_CHAT_QUERY_KEY }),
  });
};
