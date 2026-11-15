import { useCallback, useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router';

/** A change of the query string, applied to the address it receives. */
export type SearchChange = (current: URLSearchParams) => URLSearchParams;

/** The query strings asked of a path and not shown yet, after the one the page shows. */
type PendingSearches = {
  readonly pathname: string;
  readonly shown: string;
  readonly requested: readonly string[];
};

// One for the whole page: the hooks of the history, of the period, of the sort and of the compared flows change the
// same address (ADR 0166). React Router hands a change the query string of the last render, so changes made before
// the page shows the previous one would overwrite each other.
let pending: PendingSearches | null = null;

// A query string the page shows drops the requests it already reflects; one nobody asked for comes from outside (a
// navigation, the back button) and forgets them all.
const synchronize = (pathname: string, shown: string): void => {
  if (pending === null) {
    return;
  }
  if (pathname !== pending.pathname) {
    pending = null;
    return;
  }
  const reached = pending.requested.indexOf(shown);
  if (reached >= 0) {
    const left = pending.requested.slice(reached + 1);
    pending = left.length === 0 ? null : { pathname, shown, requested: left };
    return;
  }
  if (shown !== pending.shown) {
    pending = null;
  }
};

const request = (pathname: string, shown: string, change: SearchChange): string => {
  synchronize(pathname, shown);
  const requested = pending?.requested ?? [];
  const next = change(new URLSearchParams(requested.at(-1) ?? shown)).toString();
  pending = { pathname, shown: pending?.shown ?? shown, requested: [...requested, next] };
  return next;
};

/**
 * The function that changes the query string of the page: every change starts from the last query string asked for,
 * not from the one of the last render, so changes made in quick succession add up (ADR 0166).
 */
export const useSearchChange = (): ((change: SearchChange) => void) => {
  const [search, setSearch] = useSearchParams();
  const { pathname } = useLocation();
  const shown = search.toString();
  useEffect(() => {
    synchronize(pathname, shown);
  }, [pathname, shown]);
  return useCallback(
    (change: SearchChange) => {
      setSearch(new URLSearchParams(request(pathname, shown, change)));
    },
    [pathname, setSearch, shown],
  );
};
