import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { useSearchChange } from '@/hooks/use-search-change';

import { searchOf, withSearch, type HistorySearch } from '../utils/history-search';

/**
 * Tab and filters live in the query string, so a search has a link and survives a reload (ADR 0139); the period of
 * the page is the shared selector's. Changes made in quick succession add up (ADR 0166).
 */
export const useHistorySearch = (): [HistorySearch, (change: Partial<HistorySearch>) => void] => {
  const [params] = useSearchParams();
  const changeSearch = useSearchChange();
  const change = useCallback(
    (values: Partial<HistorySearch>) => {
      changeSearch((current) => withSearch(current, values));
    },
    [changeSearch],
  );
  return [searchOf(params), change];
};
