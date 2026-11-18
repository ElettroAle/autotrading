import type { Locator } from '@playwright/test';

import { fakeClock } from '@/testing/mocks/clock';
import { aCompletedCycle, apiInstant } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from './dashboard-pages';

// The histories the scenarios of the periods of the menu read (R6.4.6, R6.4.7): the fake API reads the periods on a
// clock the background fixes, so the last minutes are the same minutes for every step.
export const MINUTE = 60_000;
export const QUARTER = 15 * MINUTE;
export const HOUR = 60 * MINUTE;
export const DAY = 24 * HOUR;
const HISTORY = 30 * DAY;
const INITIAL_CAPITAL = 1000;

export const minuteOf = (time: number): number => time - (time % MINUTE);

/**
 * The history of the flow, in place of the one it had: a cycle every `every` milliseconds in the last 30 days, the last
 * at `last`, each closing a position and recording an equity one USDC higher than the one before.
 */
export const recordHistory = (flow: string, last: number, every: number): void => {
  const count = Math.floor(HISTORY / every);
  const instants = Array.from(
    { length: count },
    (_, index) => new Date(last - (count - 1 - index) * every),
  );
  fakePlatform.changeFlow(flow, {
    currentCapital: INITIAL_CAPITAL + count - 1,
    history: {
      closedPositions: instants.map((closedAt) => ({ netPnl: 1, fees: 0, closedAt })),
      modelCalls: [],
    },
    equity: instants.map((plannedAt, index) => ({ plannedAt, equity: INITIAL_CAPITAL + index })),
  });
  fakePlatform.recordCycles(
    flow,
    instants.map((instant) => aCompletedCycle(instant)),
  );
  fakePlatform.recordClosedPositions(
    flow,
    instants.map((closedAt) => aClosedPosition({ closedAt })),
  );
};

export const recordFlow = (account: string, flow: string, last: number, every: number): void => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.addUser(account, { hasUserRole: true });
  }
  fakePlatform.addFlow(account, flow, { allocatedCapital: INITIAL_CAPITAL });
  recordHistory(flow, last, every);
};

/** The last instant at the time of the day, in the time zone the browser shares with the steps, not after `before`. */
export const lastAt = (time: string, before: number): Date => {
  const [hours = 0, minutes = 0] = time.split(':').map(Number);
  const instant = new Date(before);
  instant.setHours(hours, minutes, 0, 0);
  return instant.getTime() > before ? new Date(instant.getTime() - DAY) : instant;
};

export const minutesAgo = (minutes: number): Date => new Date(fakeClock.now() - minutes * MINUTE);

export const pointAt = (dashboard: DashboardPages, instant: Date): Locator =>
  dashboard.equityCurve().locator(`circle[data-planned-at^="${apiInstant(instant).slice(0, 16)}"]`);
