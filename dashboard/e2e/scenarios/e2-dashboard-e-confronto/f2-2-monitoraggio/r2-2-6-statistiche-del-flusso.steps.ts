import { expect } from '@playwright/test';

import { emptyHistory, fakePlatform, type FakeFlowHistory } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const DAY_MS = 24 * 60 * 60 * 1000;
const LONG_AGO_DAYS = 20;
const RECENT_DAYS = 2;

const daysAgo = (days: number): Date => new Date(Date.now() - days * DAY_MS);

const amount = (text: string): number => Number(text.replace(',', '.'));

const amounts = (text: string): number[] => text.replace(' e ', ', ').split(', ').map(amount);

const historyOf = (memory: ScenarioMemory, flow: string): FakeFlowHistory => {
  const history = memory.histories.get(flow) ?? emptyHistory();
  memory.histories.set(flow, history);
  return history;
};

const onlyHistory = (memory: ScenarioMemory): FakeFlowHistory => {
  const [history] = [...memory.histories.values()];
  if (history === undefined || memory.histories.size !== 1) {
    throw new Error('the scenario prepares exactly one flow');
  }
  return history;
};

/** The flows the scenario prepared become flows of the user, who opens the page of one of them. */
const openStatistics = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  flow: string,
): Promise<void> => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.addUser(account, { hasUserRole: true });
  }
  for (const [name, history] of memory.histories) {
    fakePlatform.addFlow(account, name, { history });
  }
  await dashboard.openFlow(flow);
  await dashboard.signInAs(account);
  await expect(dashboard.statistics()).toBeVisible();
};

Given(
  /^che il flusso "([^"]+)" ha chiuso \d+ posizioni con PnL netto (.+) USDC e commissioni totali ([\d,]+) USDC$/,
  async ({ memory }, flow: string, results: string, fees: string) => {
    const nets = amounts(results);
    const share = amount(fees) / nets.length;
    historyOf(memory, flow).closedPositions.push(
      ...nets.map((netPnl) => ({ netPnl, fees: share, closedAt: daysAgo(LONG_AGO_DAYS) })),
    );
  },
);

Given(
  /^che le chiamate al modello del flusso sono costate ([\d,]+) USD$/,
  async ({ memory }, cost: string) => {
    onlyHistory(memory).modelCalls.push({
      costUsd: amount(cost),
      plannedAt: daysAgo(LONG_AGO_DAYS),
    });
  },
);

Given(
  /^che solo le posizioni con PnL (.+) USDC sono state chiuse negli ultimi 7 giorni$/,
  async ({ memory }, results: string) => {
    const recent = amounts(results);
    const history = onlyHistory(memory);
    history.closedPositions.forEach((position, index) => {
      if (recent.includes(position.netPnl)) {
        history.closedPositions[index] = { ...position, closedAt: daysAgo(RECENT_DAYS) };
      }
    });
  },
);

Given(
  /^che il flusso "([^"]+)" chiude una quinta posizione con PnL netto ([+-]?[\d,]+) USDC$/,
  async ({ memory }, flow: string, result: string) => {
    historyOf(memory, flow).closedPositions.push({
      netPnl: amount(result),
      fees: 0,
      closedAt: daysAgo(RECENT_DAYS),
    });
  },
);

When(
  '{string} apre le statistiche del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await openStatistics(dashboard, memory, account, flow);
  },
);

Then(
  /^vede (\d+) vinte, (\d+) perse, win rate ([\d,]+%), PnL medio vincenti ([+-][\d,]+ USDC), PnL medio perdenti ([+-][\d,]+ USDC), commissioni ([\d,]+ USDC), (\d+) operazioni, costo del modello ([\d,]+ USD)$/,
  async (
    { dashboard },
    won: number,
    lost: number,
    rate: string,
    winning: string,
    losing: string,
    fees: string,
    operations: number,
    cost: string,
  ) => {
    await expect(dashboard.statistic('Operazioni vinte')).toHaveText(String(won));
    await expect(dashboard.statistic('Operazioni perse')).toHaveText(String(lost));
    await expect(dashboard.statistic('Win rate')).toHaveText(rate);
    await expect(dashboard.statistic('PnL medio delle vincenti')).toHaveText(winning);
    await expect(dashboard.statistic('PnL medio delle perdenti')).toHaveText(losing);
    await expect(dashboard.statistic('Commissioni totali')).toHaveText(fees);
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(operations));
    await expect(dashboard.statistic('Costo del modello IA')).toHaveText(cost);
  },
);

Then(
  /^vede (\d+) vinta, (\d+) persa e (\d+) operazioni$/,
  async ({ dashboard }, won: number, lost: number, operations: number) => {
    await expect(dashboard.statistic('Operazioni vinte')).toHaveText(String(won));
    await expect(dashboard.statistic('Operazioni perse')).toHaveText(String(lost));
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(operations));
  },
);

Then(
  /^vede (\d+) vinte, (\d+) perse, win rate ([\d,]+%) e (\d+) operazioni$/,
  async ({ dashboard }, won: number, lost: number, rate: string, operations: number) => {
    await expect(dashboard.statistic('Operazioni vinte')).toHaveText(String(won));
    await expect(dashboard.statistic('Operazioni perse')).toHaveText(String(lost));
    await expect(dashboard.statistic('Win rate')).toHaveText(rate);
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(operations));
  },
);

Then(
  /^vede (\d+) operazioni e win rate "([^"]+)"$/,
  async ({ dashboard }, operations: number, rate: string) => {
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(operations));
    await expect(dashboard.statistic('Win rate')).toHaveText(rate);
  },
);
