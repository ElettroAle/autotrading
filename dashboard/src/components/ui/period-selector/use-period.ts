import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

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

const PERIOD = 'period';
const FROM = 'from';
const TO = 'to';

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
const withPeriod = (current: URLSearchParams, period: Period): URLSearchParams => {
  const next = new URLSearchParams(current);
  [PERIOD, FROM, TO].forEach((name) => next.delete(name));
  searchOf(period).forEach((value, name) => {
    if (value !== '' && !(name === PERIOD && value === 'all')) {
      next.set(name, value);
    }
  });
  return next;
};

/** The query string of the API for the period: the days only for a range. */
export const apiSearchOf = (period: Period): string => searchOf(period).toString();

/** A range waits for both its days before the panels read it. */
export const isComplete = (period: Period): boolean =>
  period.kind !== 'range' || (period.from !== '' && period.to !== '');

/**
 * The period lives in the query string of the page, so it survives a reload and every panel of the page reads the
 * same one (ADR 0123). Without one, or with one the page does not know, it is the whole life.
 */
export const usePeriod = (): [Period, (period: Period) => void] => {
  const [search, setSearch] = useSearchParams();
  const kind = search.get(PERIOD);
  const period: Period = isKind(kind)
    ? { kind, from: search.get(FROM) ?? '', to: search.get(TO) ?? '' }
    : { kind: 'all', from: '', to: '' };
  const choose = useCallback(
    (chosen: Period) => {
      setSearch((current) => withPeriod(current, chosen));
    },
    [setSearch],
  );
  return [period, choose];
};
