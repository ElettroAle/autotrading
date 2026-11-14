import { useQueryClient, type Query } from '@tanstack/react-query';
import { useCallback, useSyncExternalStore } from 'react';

import { PAGE_DATA } from '@/lib/react-query';

export type PageData = {
  /** When the data the page shows was last read, in milliseconds since the epoch; 0 before the first reading. */
  readonly updatedAt: number;
  /** A rereading failed: the page still shows the data of the last reading. */
  readonly stale: boolean;
  readonly refresh: () => Promise<void>;
};

const isPageData = (query: Query): boolean => query.meta?.[PAGE_DATA] === true;

const isStale = (query: Query): boolean =>
  query.state.status === 'error' && query.state.data !== undefined;

/** The freshness of the data of the open page, from its queries in the cache (ADR 0119). */
export const usePageData = (): PageData => {
  const queryClient = useQueryClient();
  const cache = queryClient.getQueryCache();
  const subscribe = useCallback((onChange: () => void) => cache.subscribe(onChange), [cache]);
  const pageQueries = () => cache.findAll({ predicate: isPageData, type: 'active' });
  const updatedAt = useSyncExternalStore(subscribe, () =>
    Math.max(0, ...pageQueries().map((query) => query.state.dataUpdatedAt)),
  );
  const stale = useSyncExternalStore(subscribe, () => pageQueries().some(isStale));
  const refresh = useCallback(
    () => queryClient.invalidateQueries({ predicate: isPageData }),
    [queryClient],
  );
  return { updatedAt, stale, refresh };
};
