import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

const DAY = 24 * 60 * 60 * 1000;
const COMPARED_PERIOD = '30 giorni';
// A cycle before the period, so the curve starts from the first point of the period and not of the flow.
const BEFORE_THE_PERIOD = 40 * DAY;
const DAYS_OF_THE_CYCLES = [20, 10, 5, 1];
const EQUITY_OF_THE_CYCLES: Record<string, number[]> = {
  alfa: [300, 330, 297, 360],
  beta: [200, 210, 190, 220],
};
const OTHER_EQUITY = [100, 104, 99, 110];

const giveFlowWithCycles = (account: string, flow: string): void => {
  fakePlatform.addFlow(account, flow);
  const now = Date.now();
  fakePlatform.recordEquity(flow, new Date(now - BEFORE_THE_PERIOD), 1000);
  const equity = EQUITY_OF_THE_CYCLES[flow] ?? OTHER_EQUITY;
  DAYS_OF_THE_CYCLES.forEach((days, index) => {
    fakePlatform.recordEquity(flow, new Date(now - days * DAY), equity[index] ?? 0);
  });
};

const openRankingOfThePeriod = async (dashboard: DashboardPages, account: string) => {
  await dashboard.openRanking();
  await dashboard.signInAs(account);
  await dashboard.period().selectOption({ label: COMPARED_PERIOD });
  await expect(dashboard.rankingRows().first()).toBeVisible();
};

const choose = async (dashboard: DashboardPages, flow: string) => {
  // The box reflects the query string, which changes after the click: the state is awaited, not read at once.
  await dashboard.compareBox(flow).click();
  await expect(dashboard.compareBox(flow)).toBeChecked();
};

Given(
  'che {string} ha i flussi {string} e {string} con cicli negli ultimi {int} giorni',
  async ({ memory }, account: string, first: string, second: string, days: number) => {
    expect(Math.max(...DAYS_OF_THE_CYCLES) * DAY).toBeLessThan(days * DAY);
    expect(BEFORE_THE_PERIOD).toBeGreaterThan(days * DAY);
    fakePlatform.addUser(account, { hasUserRole: true });
    giveFlowWithCycles(account, first);
    giveFlowWithCycles(account, second);
    memory.account = account;
  },
);

Given(
  'che {string} ha {int} flussi con cicli nel periodo',
  async ({}, account: string, count: number) => {
    const others = count - Object.keys(EQUITY_OF_THE_CYCLES).length;
    for (let index = 1; index <= others; index += 1) {
      giveFlowWithCycles(account, `flusso ${index}`);
    }
  },
);

When(
  /^"([^"]+)" sceglie "([^"]+)" e "([^"]+)" nella classifica del periodo "([^"]+)" e apre il confronto$/,
  async ({ dashboard }, account: string, first: string, second: string, period: string) => {
    expect(period).toBe(COMPARED_PERIOD);
    await openRankingOfThePeriod(dashboard, account);
    await choose(dashboard, first);
    await choose(dashboard, second);
    await dashboard.compareLink().click();
    await expect(dashboard.comparisonChart()).toBeVisible();
  },
);

When(
  '{string} ne ha scelti {int}',
  async ({ dashboard, memory }, account: string, count: number) => {
    expect(account).toBe(memory.account);
    await openRankingOfThePeriod(dashboard, account);
    const flows = await dashboard.rankingRows().getByRole('link').allInnerTexts();
    for (const flow of flows.slice(0, count)) {
      await choose(dashboard, flow);
    }
    memory.flow = flows[count] ?? '';
  },
);

Then(
  'vede le due curve sullo stesso grafico, ciascuna da 0% al primo punto del periodo',
  async ({ dashboard }) => {
    for (const flow of Object.keys(EQUITY_OF_THE_CYCLES)) {
      const points = dashboard.comparisonPoints(flow);
      await expect(points).toHaveCount(DAYS_OF_THE_CYCLES.length);
      await expect(points.first()).toHaveAccessibleName(new RegExp(`^${flow} 0,00% del `));
    }
  },
);

Then(
  'la legenda mostra {string} e {string} con colori distinti',
  async ({ dashboard }, first: string, second: string) => {
    const colorOf = (flow: string) =>
      dashboard
        .legendEntry(flow)
        .locator('span')
        .evaluate((swatch) => getComputedStyle(swatch).backgroundColor);
    await expect(dashboard.legendEntry(first)).toBeVisible();
    await expect(dashboard.legendEntry(second)).toBeVisible();
    expect(await colorOf(first)).not.toBe(await colorOf(second));
  },
);

Then('non può sceglierne un sesto', async ({ dashboard, memory }) => {
  await expect(dashboard.compareBox(memory.flow)).toBeVisible();
  await expect(dashboard.compareBox(memory.flow)).toBeDisabled();
  await expect(dashboard.compareBox(memory.flow)).not.toBeChecked();
});
