import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

const USER = 'anna';
const CYCLE = 15 * 60 * 1000;
const DAY = 24 * 60 * 60 * 1000;
const GREEN = '#16a34a';
const RED = '#dc2626';

const flowOf = (name: string, initialCapital = '100') => {
  if (!fakePlatform.hasUser(USER)) {
    fakePlatform.addUser(USER, { hasUserRole: true });
  }
  return fakePlatform.addFlow(USER, name, undefined, { initialCapital });
};

Given(
  'che il flusso {string} ha capitale iniziale {int} USDC',
  async ({ memory }, flow: string, capital: number) => {
    flowOf(flow, String(capital));
    memory.flow = flow;
  },
);

Given(
  'che i suoi ultimi tre cicli hanno registrato equity {int}, {int} e {int} USDC',
  async ({ memory }, first: number, second: number, third: number) => {
    const now = Date.now();
    [first, second, third].forEach((equity, index) => {
      fakePlatform.recordEquity(memory.flow, new Date(now - (3 - index) * CYCLE), equity);
    });
  },
);

Given(
  'che il flusso {string} ha cicli negli ultimi {int} giorni',
  async ({}, flow: string, days: number) => {
    const now = Date.now();
    for (let day = 1; day <= days; day += 1) {
      fakePlatform.recordEquity(flow, new Date(now - day * DAY), 300 + (day % 7));
    }
  },
);

Given('che il flusso {string} non ha ancora cicli', async ({}, flow: string) => {
  flowOf(flow);
});

When(
  "{string} apre l'equity curve del flusso {string}",
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlow(flow);
    await dashboard.signInAs(account);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

Then(
  "i punti a {int} e {int} USDC sono nell'area verde",
  async ({ dashboard }, first: number, second: number) => {
    for (const equity of [first, second]) {
      await expect(dashboard.equityPoint(equity)).toHaveAccessibleName(/nell'area verde$/);
      await expect(dashboard.equityPoint(equity)).toHaveAttribute('fill', GREEN);
    }
  },
);

Then("il punto a {int} USDC è nell'area rossa", async ({ dashboard }, equity: number) => {
  await expect(dashboard.equityPoint(equity)).toHaveAccessibleName(/nell'area rossa$/);
  await expect(dashboard.equityPoint(equity)).toHaveAttribute('fill', RED);
});

Then(
  'la curva mostra solo i punti degli ultimi {int} giorni',
  async ({ dashboard, memory }, days: number) => {
    const since = Date.now() - days * DAY;
    const expected = fakePlatform
      .flowNamed(memory.flow)
      .equity.filter((point) => point.plannedAt.getTime() >= since).length;
    await expect(dashboard.equityPoints()).toHaveCount(expected);
    const shown = await dashboard
      .equityPoints()
      .evaluateAll((points) =>
        points.map((point) => Date.parse(point.getAttribute('data-planned-at') ?? '')),
      );
    expect(shown.every((instant) => instant >= since)).toBe(true);
    expect(expected).toBeLessThan(fakePlatform.flowNamed(memory.flow).equity.length);
  },
);

Then('la pagina mostra {string}', async ({ dashboard }, message: string) => {
  await expect(dashboard.page.getByText(message, { exact: true })).toBeVisible();
  await expect(dashboard.equityCurve()).toHaveCount(0);
});
