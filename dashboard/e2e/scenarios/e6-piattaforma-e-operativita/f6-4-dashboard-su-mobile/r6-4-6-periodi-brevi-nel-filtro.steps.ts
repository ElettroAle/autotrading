import { expect, type Locator } from '@playwright/test';

import { fakeClock } from '@/testing/mocks/clock';
import { aCompletedCycle, apiInstant } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';
import { formatPercent } from '@/utils/format-amount';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// R6.4.6, ADR periodi-brevi-come-durata-nel-dominio and periodi-brevi-nel-selettore-condiviso. The fake API reads the
// periods on a clock the background fixes, so the last minutes are the same minutes for every step.
const MINUTE = 60_000;
const QUARTER = 15 * MINUTE;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const HISTORY = 30 * DAY;
const INITIAL_CAPITAL = 1000;
const FLOW_TABS = 'Dati del flusso';

const minuteOf = (time: number): number => time - (time % MINUTE);

/**
 * The history of the flow, in place of the one it had: a cycle every `every` milliseconds in the last 30 days, the last
 * at `last`, each closing a position and recording an equity one USDC higher than the one before.
 */
const recordHistory = (flow: string, last: number, every: number): void => {
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

const recordFlow = (account: string, flow: string, last: number, every: number): void => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.addUser(account, { hasUserRole: true });
  }
  fakePlatform.addFlow(account, flow, { allocatedCapital: INITIAL_CAPITAL });
  recordHistory(flow, last, every);
};

/** The last instant at the time of the day, in the time zone the browser shares with the steps, not after `before`. */
const lastAt = (time: string, before: number): Date => {
  const [hours = 0, minutes = 0] = time.split(':').map(Number);
  const instant = new Date(before);
  instant.setHours(hours, minutes, 0, 0);
  return instant.getTime() > before ? new Date(instant.getTime() - DAY) : instant;
};

const minutesAgo = (minutes: number): Date => new Date(fakeClock.now() - minutes * MINUTE);

const pointAt = (dashboard: DashboardPages, instant: Date): Locator =>
  dashboard.equityCurve().locator(`circle[data-planned-at^="${apiInstant(instant).slice(0, 16)}"]`);

const tab = (dashboard: DashboardPages, name: string): Locator =>
  dashboard
    .content()
    .getByRole('navigation', { name: FLOW_TABS })
    .getByRole('link', { name, exact: true });

const equitySection = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByRole('region', { name: 'Equity curve' });

const mentioning = (text: string): RegExp =>
  new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');

Given(
  'che {string} ha il flusso {string} con un ciclo ogni 15 minuti negli ultimi 30 giorni',
  async ({ memory }, account: string, flow: string) => {
    const now = Date.now();
    fakeClock.fix(new Date(now));
    recordFlow(account, flow, now - (now % QUARTER), QUARTER);
    memory.owner = account;
    memory.flow = flow;
  },
);

// The platform as it was at the last time of the day not after now: its cycles end there.
Given('che sono le {word}', async ({ memory }, time: string) => {
  const instant = lastAt(time, fakeClock.now());
  fakeClock.fix(instant);
  recordHistory(memory.flow, instant.getTime(), QUARTER);
});

Given(
  "che il flusso {string} ha un ciclo ogni {int} minuti e l'ultimo {int} minuti fa",
  async ({ memory }, flow: string, every: number, ago: number) => {
    recordFlow(memory.owner, flow, minutesAgo(ago).getTime(), every * MINUTE);
  },
);

Given(
  "che l'ultimo ciclo del flusso {string} è di {int} minuti fa",
  async ({ memory }, flow: string, ago: number) => {
    recordFlow(memory.owner, flow, minutesAgo(ago).getTime(), HOUR);
  },
);

When(
  '{string} apre il menu del periodo nella pagina del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.period()).toBeVisible();
  },
);

When(
  '{string} sceglie il periodo {string} nella classifica dei flussi',
  async ({ dashboard }, account: string, period: string) => {
    await dashboard.openRanking();
    await dashboard.signInAs(account);
    await dashboard.period().selectOption({ label: period });
    await expect(dashboard.period().locator('option:checked')).toHaveText(period);
  },
);

Then(/^vede in ordine (.+)$/, async ({ dashboard }, labels: string) => {
  const expected = labels.split(', ').map((label) => label.replaceAll('"', ''));
  await expect(dashboard.period().locator('option')).toHaveText(expected);
});

Then('il periodo scelto è {string}', async ({ dashboard }, label: string) => {
  await expect(dashboard.period().locator('option:checked')).toHaveText(label);
});

Then(
  'riepilogo, equity curve, statistiche, posizioni chiuse e cicli valgono dalle {word} a ora',
  async ({ dashboard }, time: string) => {
    const now = fakeClock.now();
    const since = lastAt(time, now);
    const cycles = Math.floor((minuteOf(now) - since.getTime()) / QUARTER) + 1;
    await expect(dashboard.equityPoints()).toHaveCount(cycles);
    await expect(pointAt(dashboard, since)).toBeVisible();
    await expect(dashboard.result('Guadagno nel periodo')).toContainText(`+${cycles - 1},00 USDC`);
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(cycles));
    // The lists ask from the minute the browser reads: the same instant as the API.
    await dashboard.page.clock.setFixedTime(new Date(now));
    await tab(dashboard, 'Posizioni chiuse').click();
    await expect(dashboard.closedPositionRows()).toHaveCount(cycles);
    await tab(dashboard, 'Cicli').click();
    await expect(dashboard.cycleRows()).toHaveCount(cycles);
  },
);

Then(
  "l'indirizzo della pagina porta il periodo {string}",
  async ({ dashboard }, period: string) => {
    await expect(dashboard.page).toHaveURL(new RegExp(`[?&]period=${period}(&|$)`));
  },
);

Then(
  'il rendimento di ogni flusso è calcolato sulle ultime 24 ore',
  async ({ dashboard, memory }) => {
    const since = minuteOf(fakeClock.now()) - DAY;
    const flow = fakePlatform.flowNamed(memory.flow);
    const curve = flow.equity
      .filter(
        (point) =>
          point.plannedAt.getTime() >= since && point.plannedAt.getTime() <= fakeClock.now(),
      )
      .map((point) => point.equity);
    const first = curve[0] ?? 0;
    const last = curve.at(-1) ?? 0;
    const expected = formatPercent((((last - first) / first) * 100).toFixed(2));
    await expect(await dashboard.rankingCell(memory.flow, 'Rendimento')).toHaveText(expected, {
      useInnerText: true,
    });
  },
);

Then(
  "l'equity curve mostra il solo punto del ciclo di {int} minuti fa",
  async ({ dashboard }, ago: number) => {
    await expect(dashboard.equityPoints()).toHaveCount(1);
    await expect(pointAt(dashboard, minutesAgo(ago))).toBeVisible();
  },
);

Then("l'equity curve dice {string}", async ({ dashboard }, text: string) => {
  await expect(equitySection(dashboard)).toContainText(mentioning(text));
  await expect(dashboard.equityCurve()).toHaveCount(0);
});

Then('le statistiche dicono {string}', async ({ dashboard }, text: string) => {
  await expect(dashboard.statistics()).toContainText(mentioning(text));
});
