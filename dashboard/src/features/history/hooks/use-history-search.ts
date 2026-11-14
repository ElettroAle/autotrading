import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { searchOf, withSearch, type HistorySearch } from '../utils/history-search';

/**
 * Tab and filters live in the query string, so a search has a link and survives a reload (ADR 0139); the period of
 * the page is the shared selector's.
 */
export const useHistorySearch = (): [HistorySearch, (change: Partial<HistorySearch>) => void] => {
  const [params, setParams] = useSearchParams();
  const change = useCallback(
    (values: Partial<HistorySearch>) => {
      setParams((current) => withSearch(current, values));
    },
    [setParams],
  );
  return [searchOf(params), change];
};
