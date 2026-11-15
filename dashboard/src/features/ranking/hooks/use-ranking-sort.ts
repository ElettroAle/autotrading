import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import type { DataTableSort } from '@/components/ui/data-table';
import { useSearchChange } from '@/hooks/use-search-change';

import { DEFAULT_RANKING_SORT, isRankingSortKey } from '../utils/sort-ranking';

const SORT = 'sort';
const ORDER = 'order';
const ASCENDING = 'asc';
const DESCENDING = 'desc';

const isDefault = (sort: DataTableSort): boolean =>
  sort.key === DEFAULT_RANKING_SORT.key && sort.direction === DEFAULT_RANKING_SORT.direction;

// The same column turns the order; another column starts from its highest values, as the ranking does.
const nextSort = (current: DataTableSort, key: string): DataTableSort =>
  current.key === key
    ? { key, direction: current.direction === 'ascending' ? 'descending' : 'ascending' }
    : { key, direction: 'descending' };

// Without a sort, or with a column the ranking does not know, the order is the API's.
const sortIn = (search: URLSearchParams): DataTableSort => {
  const key = search.get(SORT);
  return isRankingSortKey(key)
    ? { key, direction: search.get(ORDER) === ASCENDING ? 'ascending' : 'descending' }
    : DEFAULT_RANKING_SORT;
};

const withSort = (current: URLSearchParams, sort: DataTableSort): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.delete(SORT);
  next.delete(ORDER);
  if (!isDefault(sort)) {
    next.set(SORT, sort.key);
    next.set(ORDER, sort.direction === 'ascending' ? ASCENDING : DESCENDING);
  }
  return next;
};

/**
 * The column and the order of the ranking live in the query string, so a sorted ranking has a link of its own
 * (ADR 0136); a column chosen twice in quick succession turns the order (ADR 0166).
 */
export const useRankingSort = (): [DataTableSort, (key: string) => void] => {
  const [search] = useSearchParams();
  const changeSearch = useSearchChange();
  const sortBy = useCallback(
    (chosen: string) => {
      changeSearch((current) => withSort(current, nextSort(sortIn(current), chosen)));
    },
    [changeSearch],
  );
  return [sortIn(search), sortBy];
};
