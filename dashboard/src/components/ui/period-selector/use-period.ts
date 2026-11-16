import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { useSearchChange } from '@/hooks/use-search-change';

/** The periods the API accepts, with the words the page shows (ADR 0122). */
export const PERIODS = [
  { kind: 'all', label: 'Tutta la vita' },
  { kind: '7d', label: '7 giorni' },
  { kind: '30d', label: '30 giorni' },
  { kind: 'range', label: 'Intervallo' },
] as const;

export type PeriodKind = (typeof PERIODS)[number]['kind'];

/** A period of the page; `from` and `to` are the days of a range, empty until chosen. */
export type Period = { readonly kind: PeriodKind; readonly from: string; readonly to: string };

/** The days of an interval chosen on a chart, both whole, as the API reads them. */
export type Interval = { readonly from: string; readonly to: string };

/** The days a list of the API is asked for, absent where the period does not limit. */
export type ListDays = { readonly from?: string; readonly to?: string };

const PERIOD = 'period';
const FROM = 'from';
const TO = 'to';
const PAGE = 'page';
const DAY_MS = 24 * 60 * 60 * 1000;
const LAST_DAYS: Partial<Record<PeriodKind, number>> = { '7d': 7, '30d': 30 };

const isKind = (value: string | null): value is PeriodKind =>
  PERIODS.some((period) => period.kind === value);

const searchOf = (period: Period): URLSearchParams => {
  const search = new URLSearchParams({ [PERIOD]: period.kind });
  if (period.kind === 'range') {
    search.set(FROM, period.from);
    search.set(TO, period.to);
  }
  return search;
};

// The other parameters of the page stay; the whole life, the default, and the days not chosen yet leave no trace.
// Another period shows other rows, so the lists start again from their first page.
const withPeriod = (current: URLSearchParams, period: Period): URLSearchParams => {
  const next = new URLSearchParams(current);
  [PERIOD, FROM, TO, PAGE].forEach((name) => next.delete(name));
  searchOf(period).forEach((value, name) => {
    if (value !== '' && !(name === PERIOD && value === 'all')) {
      next.set(name, value);
    }
  });
  return next;
};

const withInterval = (current: URLSearchParams, interval: Interval): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.delete(PAGE);
  next.set(FROM, interval.from);
  next.set(TO, interval.to);
  return next;
};

const withoutInterval = (current: URLSearchParams): URLSearchParams => {
  const next = new URLSearchParams(current);
  [FROM, TO, PAGE].forEach((name) => next.delete(name));
  return next;
};

/** The period chosen in the menu; without one, or with one the page does not know, it is the whole life. */
const menuPeriodOf = (search: URLSearchParams): Period => {
  const kind = search.get(PERIOD);
  return isKind(kind)
    ? { kind, from: search.get(FROM) ?? '', to: search.get(TO) ?? '' }
    : { kind: 'all', from: '', to: '' };
};

// The days beside a period of the menu other than a range are an interval chosen on a chart: they win over the menu
// until removed (ADR intervallo-trascinando-sull-equity-curve).
const intervalOf = (search: URLSearchParams): Interval | undefined => {
  const from = search.get(FROM) ?? '';
  const to = search.get(TO) ?? '';
  if (menuPeriodOf(search).kind === 'range' || from === '' || to === '') {
    return undefined;
  }
  return { from, to };
};

const effectivePeriodOf = (search: URLSearchParams): Period => {
  const interval = intervalOf(search);
  return interval === undefined ? menuPeriodOf(search) : { kind: 'range', ...interval };
};

const dayOf = (instant: Date): string => instant.toISOString().slice(0, 10);

const localDayOf = (instant: string): string => {
  const date = new Date(instant);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
};

/** The query string of the API for the period: the days only for a range. */
export const apiSearchOf = (period: Period): string => searchOf(period).toString();

/** A range waits for both its days before the panels read it. */
export const isComplete = (period: Period): boolean =>
  period.kind !== 'range' || (period.from !== '' && period.to !== '');

/**
 * The days a list of the API (cycles, closed positions) is asked for in the period: the lists take days, so the last 7
 * or 30 days start from the whole day they begin in, and the list holds every row the period holds.
 */
export const listDaysOf = (period: Period, now: Date): ListDays => {
  if (period.kind === 'range') {
    return { from: period.from, to: period.to };
  }
  const days = LAST_DAYS[period.kind];
  return days === undefined ? {} : { from: dayOf(new Date(now.getTime() - days * DAY_MS)) };
};

/** The days of two instants of a chart, the earlier first, as the user reads them in the time zone of the browser. */
export const daysOfInstants = (first: string, second: string): Interval => {
  const [from = '', to = ''] = [localDayOf(first), localDayOf(second)].sort();
  return { from, to };
};

/**
 * The period of the menu, which lives in the query string of the page, so it survives a reload and every panel of the
 * page reads the same one (ADR 0123); a period chosen right after another change of the page adds up to it (ADR 0166).
 */
export const useMenuPeriod = (): [Period, (period: Period) => void] => {
  const [search] = useSearchParams();
  const changeSearch = useSearchChange();
  const choose = useCallback(
    (chosen: Period) => {
      changeSearch((current) => withPeriod(current, chosen));
    },
    [changeSearch],
  );
  return [menuPeriodOf(search), choose];
};

/** The period every panel of the page reads: the interval chosen on a chart, or else the period of the menu. */
export const usePeriod = (): [Period, (period: Period) => void] => {
  const [search] = useSearchParams();
  const [, choose] = useMenuPeriod();
  return [effectivePeriodOf(search), choose];
};

/** The interval chosen on a chart, with the commands that choose and remove it. */
export const usePeriodInterval = () => {
  const [search] = useSearchParams();
  const changeSearch = useSearchChange();
  const interval = intervalOf(search);
  const chooseInterval = useCallback(
    (chosen: Interval) => {
      changeSearch((current) => withInterval(current, chosen));
    },
    [changeSearch],
  );
  const clearInterval = useCallback(() => {
    changeSearch((current) =>
      intervalOf(current) === undefined ? current : withoutInterval(current),
    );
  }, [changeSearch]);
  return { interval, chooseInterval, clearInterval };
};

/** The query string of the period and of the interval alone, for a link that keeps them on another view. */
export const usePeriodSearch = (): string => {
  const [search] = useSearchParams();
  const kept = new URLSearchParams();
  [PERIOD, FROM, TO].forEach((name) => {
    const value = search.get(name);
    if (value !== null && value !== '') {
      kept.set(name, value);
    }
  });
  const query = kept.toString();
  return query === '' ? '' : `?${query}`;
};
