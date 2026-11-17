import { fakeClock } from './clock';
import type { FakeFlowHistory } from './platform';

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const LAST_DURATIONS_MS: Record<string, number> = {
  '30m': 30 * MINUTE_MS,
  '1h': HOUR_MS,
  '12h': 12 * HOUR_MS,
  '24h': 24 * HOUR_MS,
  '7d': 7 * DAY_MS,
  '30d': 30 * DAY_MS,
};
const PERIOD_NAMES = ['30m', '1h', '12h', '24h', '7d', '30d', 'all', 'range'];

export type Window = { readonly since?: number; readonly until?: number };

/** The answer of the API to a period it rejects, with the reason it gives (ADR 0122). */
export class InvalidPeriod extends Error {}

const ZONE = /(Z|[+-]\d{2}:?\d{2})$/;

const wholeMinute = (time: number): number => time - (time % MINUTE_MS);

/**
 * The minute of an instant of the query string, as the API reads it (ADR periodo-al-minuto): ISO 8601, in UTC without
 * a zone, a date alone its midnight in UTC.
 */
export const minuteOf = (text: string): number => {
  const withTime = text.includes('T') ? text : `${text}T00:00`;
  return wholeMinute(Date.parse(ZONE.test(withTime) ? withTime : `${withTime}Z`));
};

/** The window of the instants `from` and `to` of the query string, the minute of `to` included. */
export const intervalWindowOf = (from: string | null, to: string | null): Window => ({
  ...(from === null ? {} : { since: minuteOf(from) }),
  ...(to === null ? {} : { until: minuteOf(to) + MINUTE_MS }),
});

// The period of the API: the whole life, the minutes from the length of a period of the last N before now to now (ADR
// periodi-brevi-come-durata-nel-dominio), or the minutes from `from` to `to` (ADR periodo-al-minuto).
export const windowOf = (search: URLSearchParams, now: number): Window => {
  const period = search.get('period') ?? 'all';
  const from = search.get('from');
  const to = search.get('to');
  if (period !== 'range' && (from !== null || to !== null)) {
    throw new InvalidPeriod('periodo non valido: inizio e fine valgono solo per un intervallo');
  }
  if (period === 'all') {
    return {};
  }
  const duration = LAST_DURATIONS_MS[period];
  if (duration !== undefined) {
    return { since: wholeMinute(now - duration), until: wholeMinute(now) + MINUTE_MS };
  }
  if (period !== 'range') {
    throw new InvalidPeriod(`periodo non valido: scegliere tra ${PERIOD_NAMES.join(', ')}`);
  }
  if (from === null || to === null) {
    throw new InvalidPeriod("periodo non valido: un intervallo ha l'inizio e la fine");
  }
  if (minuteOf(from) > minuteOf(to)) {
    throw new InvalidPeriod("periodo non valido: l'inizio è successivo alla fine");
  }
  return intervalWindowOf(from, to);
};

export const contains = (window: Window, instant: Date): boolean =>
  (window.since === undefined || instant.getTime() >= window.since) &&
  (window.until === undefined || instant.getTime() < window.until);

/** Whether an instant falls in the period of the request, as the API reads it; a period it rejects throws. */
export const periodAdmits = (
  search: URLSearchParams,
  now = fakeClock.now(),
): ((instant: Date) => boolean) => {
  const window = windowOf(search, now);
  return (instant) => contains(window, instant);
};

const sum = (values: number[]): number => values.reduce((total, value) => total + value, 0);

const averageText = (values: number[]): string | null =>
  values.length === 0 ? null : String(sum(values) / values.length);

/** The statistics of a flow as the API computes and writes them: amounts as text, null when not available. */
export const statisticsOf = (
  history: FakeFlowHistory,
  search: URLSearchParams,
  now = fakeClock.now(),
) => {
  const window = windowOf(search, now);
  const closed = history.closedPositions.filter((position) => contains(window, position.closedAt));
  const winning = closed.filter((position) => position.netPnl > 0).map((p) => p.netPnl);
  const losing = closed.filter((position) => position.netPnl < 0).map((p) => p.netPnl);
  const decisive = winning.length + losing.length;
  const calls = history.modelCalls.filter((call) => contains(window, call.plannedAt));
  return {
    won: winning.length,
    lost: losing.length,
    operations: closed.length,
    win_rate_percent: decisive === 0 ? null : ((winning.length / decisive) * 100).toFixed(2),
    average_winning_pnl: averageText(winning),
    average_losing_pnl: averageText(losing),
    total_fees: String(sum(closed.map((position) => position.fees))),
    model_cost_usd: String(sum(calls.map((call) => call.costUsd))),
    model_calls_without_cost: 0,
  };
};
