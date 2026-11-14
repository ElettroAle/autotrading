import { useInfiniteQuery } from '@tanstack/react-query';

import { useApiClient, type ApiClient } from '@/lib/api-client';

import type { HistoryKind } from '../utils/history-search';

type Page = { readonly next: string | null };

/**
 * The pages of a history with the cursor of the API: the next page starts after the last row of the previous one
 * (ADR 0138). The pages loaded are never read again by themselves (ADR 0139): only a new search starts over.
 */
export const useHistoryPages = <T extends Page>(
  kind: HistoryKind,
  query: string,
  readPage: (api: ApiClient, search: string) => Promise<T>,
  enabled: boolean,
) => {
  const api = useApiClient();
  return useInfiniteQuery({
    queryKey: ['history', kind, query],
    queryFn: ({ pageParam }) => {
      const after = pageParam === null ? '' : `&after=${encodeURIComponent(pageParam)}`;
      return readPage(api, `${query}${after}`);
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled,
    staleTime: Infinity,
    refetchInterval: false,
  });
};
