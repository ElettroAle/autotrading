import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { useSearchChange } from './use-search-change';

export type TableFilterOption = { readonly value: string; readonly label: string };

/** A filter a table declares: the parameter of the address and of the API, its label and its choices. */
export type TableFilter = {
  readonly name: string;
  readonly label: string;
  /** The words of the choice that does not narrow, «Tutti» or «Tutte». */
  readonly all: string;
  readonly options: readonly TableFilterOption[];
};

/** The chosen value of each filter, by its name; a filter not chosen is absent. */
export type TableFilterValues = Readonly<Record<string, string>>;

const PAGE = 'page';

/** The values of the declared filters in the query string: the API alone decides whether a value means anything. */
export const filterValuesOf = (
  filters: readonly TableFilter[],
  params: URLSearchParams,
): TableFilterValues =>
  Object.fromEntries(
    filters.flatMap((filter) => {
      const value = params.get(filter.name);
      return value === null || value === '' ? [] : [[filter.name, value]];
    }),
  );

/** The query string with the filter chosen, or forgotten: other results, so the list starts again from its first page. */
export const withFilter = (
  current: URLSearchParams,
  name: string,
  value: string | undefined,
): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.delete(PAGE);
  if (value === undefined) {
    next.delete(name);
  } else {
    next.set(name, value);
  }
  return next;
};

export const withoutFilters = (
  current: URLSearchParams,
  filters: readonly TableFilter[],
): URLSearchParams => {
  const next = new URLSearchParams(current);
  [PAGE, ...filters.map((filter) => filter.name)].forEach((name) => next.delete(name));
  return next;
};

/**
 * The filters of a table live in the address, so a filtered list has a link and survives a reload (R6.4.4); the
 * changes go through the shared hook of the query string (ADR 0166).
 */
export const useTableFilters = (filters: readonly TableFilter[]) => {
  const [params] = useSearchParams();
  const changeSearch = useSearchChange();
  const choose = useCallback(
    (name: string, value: string | undefined) => {
      changeSearch((current) => withFilter(current, name, value));
    },
    [changeSearch],
  );
  const reset = useCallback(() => {
    changeSearch((current) => withoutFilters(current, filters));
  }, [changeSearch, filters]);
  return { values: filterValuesOf(filters, params), choose, reset };
};
