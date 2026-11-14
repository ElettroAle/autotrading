import type { DefaultOptions } from '@tanstack/react-query';

export const queryConfig = {
  queries: {
    refetchOnWindowFocus: false,
    retry: false,
    staleTime: 60_000,
  },
} satisfies DefaultOptions;

/**
 * The mark every query of the data a page shows carries, so the page can reread them all at once. A mark, not a part
 * of the key: each feature keeps the keys it invalidates after its commands.
 */
export const PAGE_DATA = 'pageData';

export const REFRESH_INTERVAL_MS = 30_000;

/**
 * The data a page shows is reread every 30 seconds while the page is open and visible, never in the background
 * (ADR 0119). The identity of the user is not page data: it is read once.
 */
export const pageDataQuery = <const Key extends readonly unknown[]>(...key: Key) => ({
  queryKey: key,
  meta: { [PAGE_DATA]: true },
  refetchInterval: REFRESH_INTERVAL_MS,
  refetchIntervalInBackground: false,
});
