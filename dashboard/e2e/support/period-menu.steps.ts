import { expect, type Locator } from '@playwright/test';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { formatPercent } from '@/utils/format-amount';

import type { DashboardPages } from './dashboard-pages';
import { Given, Then, When } from './fixtures';
import {
  HOUR,
  QUARTER,
  lastAt,
  minuteOf,
  pointAt,
  recordFlow,
  recordHistory,
} from './period-history';

// Shared by the requirements of the periods of the menu (R6.4.6, R6.4.7; ADR periodi-brevi-come-durata-nel-dominio,
// periodi-brevi-nel-selettore-condiviso, periodo-di-6-ore-e-dall-inizio).
const FLOW_TABS = 'Dati del flusso';

const tab = (dashboard: DashboardPages, name: string): Locator =>
  dashboard
    .content()
    .getByRole('navigation', { name: FLOW_TABS })
    .getByRole('link', { name, exact: true });

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
  'il rendimento di ogni flusso è calcolato sulle ultime {int} ore',
  async ({ dashboard, memory }, hours: number) => {
    const since = minuteOf(fakeClock.now()) - hours * HOUR;
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
