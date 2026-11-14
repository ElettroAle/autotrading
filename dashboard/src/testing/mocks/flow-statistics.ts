import type { FakeFlowHistory } from './platform';

const DAY_MS = 24 * 60 * 60 * 1000;
const LAST_DAYS: Record<string, number> = { '7d': 7, '30d': 30 };

export type Window = { readonly since?: number; readonly until?: number };

/** The answer of the API to a period it rejects, with the reason it gives (ADR 0122). */
export class InvalidPeriod extends Error {}

// The period of the API: the whole life, the last 7 or 30 days, or the days from `from` to `to`, both whole, in UTC.
export const windowOf = (search: URLSearchParams, now: number): Window => {
  const period = search.get('period') ?? 'all';
  const from = search.get('from');
  const to = search.get('to');
  if (period !== 'range' && (from !== null || to !== null)) {
    throw new InvalidPeriod('periodo non valido: i giorni valgono solo per un intervallo');
  }
  if (period === 'all') {
    return {};
  }
  const days = LAST_DAYS[period];
  if (days !== undefined) {
    return { since: now - days * DAY_MS };
  }
  if (period !== 'range') {
    throw new InvalidPeriod('periodo non valido: scegliere tra all, 7d, 30d, range');
  }
  if (from === null || to === null) {
    throw new InvalidPeriod(
      'periodo non valido: un intervallo ha il giorno iniziale e il giorno finale',
    );
  }
  if (from > to) {
    throw new InvalidPeriod('periodo non valido: il giorno iniziale è successivo al giorno finale');
  }
  return { since: Date.parse(`${from}T00:00:00Z`), until: Date.parse(`${to}T00:00:00Z`) + DAY_MS };
};

export const contains = (window: Window, instant: Date): boolean =>
  (window.since === undefined || instant.getTime() >= window.since) &&
  (window.until === undefined || instant.getTime() < window.until);

/** Whether an instant falls in the period of the request, as the API reads it; a period it rejects throws. */
export const periodAdmits = (
  search: URLSearchParams,
  now = Date.now(),
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
  now = Date.now(),
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
