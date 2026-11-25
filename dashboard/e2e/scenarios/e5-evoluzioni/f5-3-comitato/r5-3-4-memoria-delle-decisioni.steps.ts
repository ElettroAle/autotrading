import { expect } from '@playwright/test';

import { aCompletedCycle, reasoningOf, type FakeAssetMemory } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The memory of the flow in the tab Decisioni, closed until opened, and in the detail of a cycle (R5.3.4, ADR
// memoria-del-flusso-dalle-decisioni-operative-precedenti): the worker composes it, the dashboard only reads it.

const USER = 'anna';
// The cycle that received the memory, at a time of a day in Italy, as the browser of the scenarios reads it.
const CYCLE_TIME = '10:07:00';
const CYCLE_AT = new Date(`2026-11-14T${CYCLE_TIME}+01:00`);
const REASONING = 'rottura della resistenza';
const MEMORY_TITLE = "Memoria dell'agente";
const MEMORY: FakeAssetMemory[] = [
  {
    asset: 'BTC',
    entries: [
      {
        planned_at: '2026-11-14T08:07:00Z',
        asset: 'BTC',
        action: 'apri',
        direction: 'long',
        price: '95000',
        reasoning: REASONING,
        outcome: { pnl: '40', realized: true },
      },
    ],
  },
];

Given('che il flusso {string} ha la memoria non attiva', async ({ memory }, flow: string) => {
  fakePlatform.ensureUser(USER);
  fakePlatform.addFlow(USER, flow, { remembered: MEMORY });
  memory.flow = flow;
  memory.cycles = [aCompletedCycle(CYCLE_AT)];
  fakePlatform.recordCycles(flow, memory.cycles);
});

Given('che il flusso {string} ha la memoria attiva', async ({ memory }, flow: string) => {
  fakePlatform.ensureUser(USER);
  fakePlatform.addFlow(USER, flow, {
    memory: { active: true, decisions: 10, days: 30 },
    remembered: MEMORY,
  });
  memory.flow = flow;
  memory.cycles = [{ ...aCompletedCycle(CYCLE_AT), memory: MEMORY }];
  fakePlatform.recordCycles(flow, memory.cycles);
});

When(
  '{string} apre le decisioni di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openDecisionsAs(account, flow);
  },
);

When(
  '{string} apre il dettaglio di un ciclo di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openCyclesOf(flow);
    await dashboard.signInAs(account);
    await dashboard.page.getByRole('link', { name: CYCLE_TIME }).click();
  },
);

Then('la memoria non è mostrata', async ({ dashboard }) => {
  // The decisions read beside where the memory would be: once they show, the page has read the flow.
  await expect(dashboard.page.getByText(reasoningOf('BTC')).first()).toBeVisible();
  await expect(dashboard.page.getByRole('group', { name: MEMORY_TITLE })).toHaveCount(0);
});

Then('la memoria è chiusa', async ({ dashboard }) => {
  await expect(dashboard.page.getByRole('group', { name: MEMORY_TITLE })).not.toHaveAttribute(
    'open',
  );
});

Then("aprendola vede ciò che l'agente riceverà al prossimo ciclo", async ({ dashboard }) => {
  const memory = dashboard.page.getByRole('group', { name: MEMORY_TITLE });
  await memory.getByText(MEMORY_TITLE).click();
  await expect(memory.getByRole('table', { name: 'Memoria di BTC' })).toContainText(REASONING);
});

Then("vede la memoria che l'agente ha ricevuto in quel ciclo", async ({ dashboard }) => {
  const received = dashboard.page.getByRole('group', { name: 'Memoria ricevuta' });
  await expect(received.getByRole('table', { name: 'Memoria di BTC' })).toContainText(REASONING);
});
