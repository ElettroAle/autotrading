import { expect } from '@playwright/test';

import { aCompletedCycle, type FakeCycleMemory } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The memory of the flow on its page and in the detail of a cycle (R5.3.4, ADR
// memoria-del-flusso-dalle-decisioni-operative-precedenti): the worker composes it, the dashboard only reads it.

const USER = 'anna';
// The cycle that received the memory, at a time of a day in Italy, as the browser of the scenarios reads it.
const CYCLE_TIME = '10:07:00';
const CYCLE_AT = new Date(`2026-11-14T${CYCLE_TIME}+01:00`);
const REASONING = 'rottura della resistenza';
const MEMORY: FakeCycleMemory[] = [
  {
    asset: 'BTC',
    decisions: [
      {
        planned_at: '2026-11-14T08:07:00Z',
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
  '{string} apre la pagina di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
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
  // The last decision reads beside where the memory would be: once it shows, the page has read the flow.
  await expect(dashboard.page.getByRole('region', { name: 'Ultima decisione' })).toBeVisible();
  await expect(dashboard.page.getByRole('region', { name: 'Memoria' })).toHaveCount(0);
});

Then("vede la memoria che l'agente ha ricevuto in quel ciclo", async ({ dashboard }) => {
  const received = dashboard.page.getByRole('group', { name: 'Memoria ricevuta' });
  await expect(received.getByRole('table', { name: 'Memoria di BTC' })).toContainText(REASONING);
});
