import { expect } from '@playwright/test';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform, flowIdOf } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

// R6.4.2, ADR riepilogo-dei-risultati-nell-api and riepilogo-dei-risultati-nella-dashboard.
const DAY = 24 * 60 * 60_000;
const PERIODS: Readonly<Record<string, string>> = { 'ultima settimana': '7d' };

const daysAgo = (days: number): Date => new Date(Date.now() - days * DAY);

const failedCycle = (days: number) =>
  aFailedCycle(aCompletedCycle(daysAgo(days)), STEPS.agentDecision, {
    errorType: 'ModelCallTimeoutError',
    message: 'il modello non ha risposto',
  });

const initialCapitalOf = (flow: string): number =>
  fakePlatform.flowNamed(flow).allocatedCapital ?? 0;

const gained = (flow: string, gain: number): void => {
  fakePlatform.changeFlow(flow, { currentCapital: initialCapitalOf(flow) + gain });
};

const openPositions = (count: number) =>
  Array.from({ length: count }, (_, index) =>
    anOpenPosition({ asset: ['BTC', 'ETH', 'SOL'][index] }),
  );

Given(
  'che {string} ha il flusso {string} con capitale iniziale {int} USDC',
  async ({ memory }, account: string, flow: string, initial: number) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, { allocatedCapital: initial, currentCapital: initial });
    memory.flow = flow;
  },
);

Given(
  "che il flusso {string} ha guadagnato {amount} USDC in tutto e {amount} USDC nell'ultima settimana",
  async ({}, flow: string, total: string, lastWeek: string) => {
    gained(flow, Number(total));
    const current = initialCapitalOf(flow) + Number(total);
    // The equity before the week does not count: the gain of the week goes from its first cycle to its last.
    fakePlatform.recordEquity(flow, daysAgo(10), initialCapitalOf(flow));
    fakePlatform.recordEquity(flow, daysAgo(6), current - Number(lastWeek));
    fakePlatform.recordEquity(flow, daysAgo(1), current);
  },
);

Given(
  "ha {int} posizione aperta e {int} cicli falliti nell'ultima settimana",
  async ({ memory }, positions: number, failed: number) => {
    fakePlatform.holdPositions(memory.flow, openPositions(positions));
    // A cycle failed before the week is out of the period.
    const inTheWeek = Array.from({ length: failed }, (_, index) => failedCycle(index + 1));
    fakePlatform.recordCycles(memory.flow, [
      failedCycle(10),
      aCompletedCycle(daysAgo(3.5)),
      ...inTheWeek,
    ]);
  },
);

Given(
  'che il flusso {string} ha perso {amount} USDC in tutto',
  async ({}, flow: string, loss: string) => {
    gained(flow, -Number(loss));
  },
);

Given(
  'che il flusso {string} ha guadagnato {amount} USDC in tutto',
  async ({}, flow: string, gain: string) => {
    gained(flow, Number(gain));
    // A flow that gained has run a cycle, so the row of the outcomes the summary replaces would have something to show.
    fakePlatform.recordCycles(flow, [aCompletedCycle(daysAgo(1))]);
  },
);

Given('che il flusso {string} non ha cicli falliti nel periodo', async ({}, flow: string) => {
  fakePlatform.recordCycles(flow, [aCompletedCycle(daysAgo(2)), aCompletedCycle(daysAgo(1))]);
});

Given(
  'che il flusso {string} ha {int} cicli falliti nel periodo',
  async ({}, flow: string, failed: number) => {
    const failures = Array.from({ length: failed }, (_, index) => failedCycle(index + 1));
    fakePlatform.recordCycles(flow, [aCompletedCycle(daysAgo(0.5)), ...failures]);
  },
);

Given(
  'che il flusso {string} ha {int} posizione aperta',
  async ({}, flow: string, count: number) => {
    fakePlatform.holdPositions(flow, openPositions(count));
  },
);

Given(
  'che il conto del flusso {string} regola in {string}',
  async ({}, flow: string, currency: string) => {
    fakePlatform.accountOfFlow(flow).currency = currency;
  },
);

When(
  '{string} apre la pagina del flusso {string} con il periodo {string}',
  async ({ dashboard, memory }, account: string, flow: string, period: string) => {
    memory.account = account;
    await dashboard.open(
      `/flows/${encodeURIComponent(flowIdOf(flow))}?period=${PERIODS[period] ?? ''}`,
    );
    await dashboard.signInAs(account);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

When(
  '{string} sceglie i cicli falliti nel riepilogo',
  async ({ dashboard, memory }, account: string) => {
    await onFlowPage(dashboard, memory, account, memory.flow);
    await dashboard.result('Cicli falliti').getByRole('link').click();
  },
);

When(
  '{string} sceglie le posizioni aperte nel riepilogo',
  async ({ dashboard, memory }, account: string) => {
    await onFlowPage(dashboard, memory, account, memory.flow);
    await dashboard.result('Posizioni aperte').getByRole('link').click();
  },
);

Then(
  'il riepilogo mostra guadagno attuale {string} e nel periodo {string}',
  async ({ dashboard }, total: string, inThePeriod: string) => {
    await expect(dashboard.result('Guadagno attuale')).toHaveText(total);
    await expect(dashboard.result('Guadagno nel periodo')).toHaveText(inThePeriod);
  },
);

Then(
  'mostra {int} posizione aperta e {int} cicli falliti',
  async ({ dashboard }, positions: number, failed: number) => {
    await expect(dashboard.result('Posizioni aperte')).toHaveText(`${positions} posizione aperta`);
    await expect(dashboard.result('Cicli falliti')).toHaveText(`${failed} cicli falliti`);
  },
);

Then('il guadagno attuale {string} è in rosso', async ({ dashboard }, total: string) => {
  await expect(dashboard.result('Guadagno attuale')).toHaveText(total);
  await expect(dashboard.result('Guadagno attuale')).toHaveClass(/text-red-/);
});

Then('il riepilogo dice {string} senza evidenza', async ({ dashboard }, words: string) => {
  const failed = dashboard.result('Cicli falliti');
  await expect(failed).toHaveText(words);
  await expect(failed).not.toHaveClass(/text-red-/);
  await expect(failed.getByRole('link')).toHaveCount(0);
});

Then(
  'vede i cicli del flusso {string} filtrati sui falliti',
  async ({ dashboard }, flow: string) => {
    // The tab Cicli of the page of the flow, in the period of the page (R6.4.3).
    await expect(dashboard.pageHeading()).toHaveText(flow);
    await expect(dashboard.flowTab('Cicli')).toHaveAttribute('aria-current', 'page');
    await expect(dashboard.page).toHaveURL(/\/cycles\?(.+&)?outcome=fallito$/);
    const rows = dashboard.page.getByRole('table', { name: 'Cicli' }).locator('tbody tr');
    await expect(rows).toHaveCount(2);
    await expect(rows).toContainText(['fallito', 'fallito']);
  },
);

Then('vede le posizioni aperte del flusso {string}', async ({ dashboard }, flow: string) => {
  // The positions held now are in the overview of the flow (R6.4.3).
  await expect(dashboard.pageHeading()).toHaveText(flow);
  await expect(dashboard.flowTab('Panoramica')).toHaveAttribute('aria-current', 'page');
  const current = dashboard.page.getByRole('region', { name: 'Posizioni aperte attuali' });
  const rows = current.getByRole('table', { name: 'Posizioni aperte' }).locator('tbody tr');
  await expect(rows).toHaveCount(1);
});

Then(
  'la scheda di {string} mostra il riepilogo e non mostra la fila degli esiti dei cicli né la voce Ambiente',
  async ({ dashboard }, flow: string) => {
    const card = dashboard.flowSummary(flow);
    await expect(dashboard.result('Guadagno attuale', card)).toHaveText('+2,50 USDC · +2,50%');
    await expect(dashboard.flowFact(flow, 'Ultima esecuzione')).toBeVisible();
    await expect(card.getByRole('list', { name: 'Esito degli ultimi cicli' })).toHaveCount(0);
    await expect(dashboard.flowFact(flow, 'Ambiente')).toHaveCount(0);
  },
);

Then('gli importi del riepilogo sono in {string}', async ({ dashboard }, currency: string) => {
  await expect(dashboard.result('Guadagno attuale')).toContainText(` ${currency}`);
  await expect(dashboard.result('Guadagno nel periodo')).toContainText(` ${currency}`);
});
