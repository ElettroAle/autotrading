import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

const CYCLE = 15 * 60 * 1000;
const DAY = 24 * 60 * 60 * 1000;
const LONG_AGO = 20 * DAY;
const RANKING_PAGE = '/ranking';
const POSITIONS: Record<string, number> = { primo: 0, secondo: 1 };

/** The equity of the cycles of the flow, oldest first: the last `recent` in the last hours, the others long ago. */
const recordCurve = (flow: string, equity: number[], recent: number): void => {
  const now = Date.now();
  const old = equity.length - recent;
  const target = fakePlatform.flowNamed(flow).equity;
  target.length = 0;
  equity.forEach((value, index) => {
    const plannedAt =
      index < old ? now - LONG_AGO - (old - index) * CYCLE : now - (equity.length - index) * CYCLE;
    target.push({ plannedAt: new Date(plannedAt), equity: value });
  });
};

const openRankingAs = async (dashboard: DashboardPages, account: string): Promise<void> => {
  await dashboard.openRanking();
  await dashboard.signInAs(account);
  await expect(dashboard.ranking()).toBeVisible();
};

const expectRankingValues = async (
  dashboard: DashboardPages,
  flow: string,
  result: string,
  drawdown: string,
): Promise<void> => {
  await expect(await dashboard.rankingCell(flow, 'Rendimento')).toHaveText(result, {
    useInnerText: true,
  });
  await expect(await dashboard.rankingCell(flow, 'Drawdown massimo')).toHaveText(drawdown, {
    useInnerText: true,
  });
};

Given(
  /^che "([^"]+)" ha il flusso "([^"]+)" con equity per ciclo ([\d, ]+) USDC$/,
  async ({ memory }, account: string, flow: string, values: string) => {
    if (!fakePlatform.hasUser(account)) {
      fakePlatform.addUser(account, { hasUserRole: true });
    }
    fakePlatform.addFlow(account, flow);
    const equity = values.split(', ').map(Number);
    recordCurve(flow, equity, equity.length);
    memory.account = account;
    memory.periodPage = RANKING_PAGE;
  },
);

Given(
  'che negli ultimi {int} giorni {string} ha equity {int} e {int} USDC',
  async ({}, days: number, flow: string, first: number, second: number) => {
    expect(days * DAY).toBeLessThan(LONG_AGO);
    const equity = fakePlatform.flowNamed(flow).equity.map((point) => point.equity);
    expect(equity.slice(-2)).toEqual([first, second]);
    recordCurve(flow, equity, 2);
  },
);

Given(
  'che il flusso {string} non ha cicli negli ultimi {int} giorni',
  async ({ memory }, flow: string, days: number) => {
    expect(days * DAY).toBeLessThan(LONG_AGO);
    fakePlatform.addFlow(memory.account, flow);
    // Cycles older than the period, with a return that would top the ranking if they counted.
    recordCurve(flow, [100, 500], 0);
  },
);

When('{string} apre la classifica', async ({ dashboard }, account: string) => {
  await openRankingAs(dashboard, account);
});

When(
  '{string} ordina la classifica per drawdown massimo crescente',
  async ({ dashboard }, account: string) => {
    await openRankingAs(dashboard, account);
    const header = dashboard.rankingHeader('Drawdown massimo');
    await header.getByRole('button').click();
    await expect(header).not.toHaveAttribute('aria-sort', 'none');
    if ((await header.getAttribute('aria-sort')) === 'descending') {
      await header.getByRole('button').click();
    }
    await expect(header).toHaveAttribute('aria-sort', 'ascending');
  },
);

Then(
  /^"([^"]+)" è (primo|secondo) con rendimento ([+-][\d,]+%) e drawdown massimo ([\d,]+%)$/,
  async ({ dashboard }, flow: string, position: string, result: string, drawdown: string) => {
    await expect(
      dashboard
        .rankingRows()
        .nth(POSITIONS[position] ?? -1)
        .getByRole('link'),
    ).toHaveText(flow);
    await expectRankingValues(dashboard, flow, result, drawdown);
  },
);

Then('{string} è primo', async ({ dashboard }, flow: string) => {
  await expect(dashboard.rankingRows().first().getByRole('link')).toHaveText(flow);
});

Then(
  /^"([^"]+)" mostra rendimento ([+-][\d,]+%) e drawdown massimo ([\d,]+%)$/,
  async ({ dashboard }, flow: string, result: string, drawdown: string) => {
    await expect(dashboard.rankingRow(flow)).toHaveCount(1);
    await expectRankingValues(dashboard, flow, result, drawdown);
  },
);

Then('la classifica non contiene {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.rankingRows().first()).toBeVisible();
  await expect(dashboard.rankingRow(flow)).toHaveCount(0);
});
