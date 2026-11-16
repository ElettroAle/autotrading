import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { useSearchChange } from '@/hooks/use-search-change';

/**
 * The periods the API accepts, with the words the page shows (ADR 0122), from the shortest (ADR
 * periodi-brevi-nel-selettore-condiviso).
 */
export const PERIODS = [
  { kind: '30m', label: '30 minuti' },
  { kind: '1h', label: '1 ora' },
  { kind: '12h', label: '12 ore' },
  { kind: '24h', label: '24 ore' },
  { kind: '7d', label: '7 giorni' },
  { kind: '30d', label: '30 giorni' },
  { kind: 'all', label: 'Tutta la vita' },
  { kind: 'range', label: 'Intervallo' },
] as const;

export type PeriodKind = (typeof PERIODS)[number]['kind'];

/**
 * A period of the page; `from` and `to` are the instants of a range, in UTC to the minute (`2026-11-16T09:15Z`), empty
 * until chosen (ADR periodo-al-minuto).
 */
export type Period = { readonly kind: PeriodKind; readonly from: string; readonly to: string };

/** The instants of an interval chosen on a chart, in UTC to the minute, as the API reads them. */
export type Interval = { readonly from: string; readonly to: string };

/** The instants a list of the API is asked for, absent where the period does not limit. */
export type ListInterval = { readonly from?: string; readonly to?: string };

const PERIOD = 'period';
const FROM = 'from';
const TO = 'to';
const PAGE = 'page';
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
// The same lengths the API gives the periods of the last minutes, hours or days (ADR
// periodi-brevi-come-durata-nel-dominio).
const LAST_DURATIONS_MS: Partial<Record<PeriodKind, number>> = {
  '30m': 30 * MINUTE_MS,
  '1h': HOUR_MS,
  '12h': 12 * HOUR_MS,
  '24h': 24 * HOUR_MS,
  '7d': 7 * DAY_MS,
  '30d': 30 * DAY_MS,
};

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

// The other parameters of the page stay; the whole life, the default, and the ends not chosen yet leave no trace.
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

// The instants beside a period of the menu other than a range are an interval chosen on a chart: they win over the menu
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

// The instant of the address: UTC, to the minute, `2026-11-16T09:15Z` (ADR periodo-al-minuto).
const minuteOf = (instant: Date): string => `${instant.toISOString().slice(0, 16)}Z`;

const twoDigits = (value: number): string => String(value).padStart(2, '0');

/** The query string of the API for the period: the instants only for a range. */
export const apiSearchOf = (period: Period): string => searchOf(period).toString();

/** A range waits for both its ends before the panels read it. */
export const isComplete = (period: Period): boolean =>
  period.kind !== 'range' || (period.from !== '' && period.to !== '');

/**
 * The instants a list of the API (cycles, closed positions) is asked for in the period: the same minutes the other
 * panels read, from the minute the length of the period before now (ADR periodo-al-minuto, ADR
 * periodi-brevi-nel-selettore-condiviso).
 */
export const listIntervalOf = (period: Period, now: Date): ListInterval => {
  if (period.kind === 'range') {
    return { from: period.from, to: period.to };
  }
  const duration = LAST_DURATIONS_MS[period.kind];
  return duration === undefined ? {} : { from: minuteOf(new Date(now.getTime() - duration)) };
};

/** The minutes of two instants of a chart, the earlier first, in UTC (ADR periodo-al-minuto). */
export const intervalOfInstants = (first: string, second: string): Interval => {
  const [earlier = 0, later = 0] = [Date.parse(first), Date.parse(second)].sort((a, b) => a - b);
  return { from: minuteOf(new Date(earlier)), to: minuteOf(new Date(later)) };
};

/** An instant of the address as a field of date and time shows it, in the time zone of the browser; empty if unread. */
export const localInputOf = (instant: string): string => {
  const date = new Date(instant);
  if (instant === '' || Number.isNaN(date.getTime())) {
    return '';
  }
  const day = `${date.getFullYear()}-${twoDigits(date.getMonth() + 1)}-${twoDigits(date.getDate())}`;
  return `${day}T${twoDigits(date.getHours())}:${twoDigits(date.getMinutes())}`;
};

/** The date and time of a field, read in the time zone of the browser, as the instant of the address. */
export const instantOfLocalInput = (value: string): string =>
  value === '' ? '' : minuteOf(new Date(value));

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
