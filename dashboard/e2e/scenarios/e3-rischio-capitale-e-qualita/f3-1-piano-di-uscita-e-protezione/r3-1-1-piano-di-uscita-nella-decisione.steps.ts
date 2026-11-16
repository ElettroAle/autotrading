import { expect } from '@playwright/test';

import { aCompletedCycle, type FakeExitPlan } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { formatPrice } from '@/utils/format-amount';

import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The cycle of the opening, at a time of a day in Italy, as the browser of the scenarios reads it.
const OPENING_TIME = '10:07:00';
const OPENED_AT = new Date(`2026-11-14T${OPENING_TIME}+01:00`);

// The flow holds the position the agent opened, with the plan in force, and the cycle of the opening recorded it.
const openLong = (memory: ScenarioMemory, flow: string, asset: string, plan: FakeExitPlan) => {
  memory.flow = flow;
  fakePlatform.holdPositions(flow, [
    anOpenPosition({
      asset,
      side: 'long',
      target: plan.target,
      stop: plan.stop,
      invalidation: plan.invalidation,
    }),
  ]);
  memory.cycles = [aCompletedCycle(OPENED_AT, asset, plan)];
  fakePlatform.recordCycles(flow, memory.cycles);
};

Given(
  'che {string} ha il flusso {string} attivo con asset {string}',
  async ({ memory }, account: string, flow: string, asset: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, { assets: [asset] });
    memory.account = account;
    memory.flow = flow;
  },
);

// The dashboard never reads the market price: the API already gives the plan the risk check kept on it (R3.1.1). The
// background only names an asset of the flow, at a price an exchange can declare.
Given(
  "che il prezzo di mercato di {string} sull'exchange del conto è {int}",
  async ({ memory }, asset: string, price: number) => {
    expect(fakePlatform.flowNamed(memory.flow).assets).toContain(asset);
    expect(price).toBeGreaterThan(0);
  },
);

Given(
  'che {string} ha aperto long su {string} con obiettivo {int}, stop {int} e invalidazione {string}',
  async (
    { memory },
    flow: string,
    asset: string,
    target: number,
    stop: number,
    invalidation: string,
  ) => {
    openLong(memory, flow, asset, { target: String(target), stop: String(stop), invalidation });
  },
);

Given(
  'che {string} ha aperto long su {string} con obiettivo {int} e stop {int}',
  async ({ memory }, flow: string, asset: string, target: number, stop: number) => {
    openLong(memory, flow, asset, {
      target: String(target),
      stop: String(stop),
      invalidation: null,
    });
  },
);

When(
  '{string} apre le posizioni aperte di {string} nella dashboard',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openPositionsOf(flow);
    await dashboard.signInAs(account);
  },
);

When(
  "{string} apre nella dashboard il dettaglio del ciclo dell'apertura",
  async ({ dashboard, memory }, account: string) => {
    await dashboard.openCyclesOf(memory.flow);
    await dashboard.signInAs(account);
    await dashboard.page.getByRole('link', { name: OPENING_TIME }).click();
  },
);

Then(
  'la posizione su {string} mostra obiettivo {int}, stop {int} e invalidazione {string}',
  async ({ dashboard }, asset: string, target: number, stop: number, invalidation: string) => {
    const row = dashboard.openPositionRows().filter({ hasText: asset });
    await expect(dashboard.cell(row, 'Obiettivo')).toHaveText(
      `Obiettivo${formatPrice(String(target))}`,
    );
    await expect(dashboard.cell(row, 'Stop')).toHaveText(`Stop${formatPrice(String(stop))}`);
    await expect(dashboard.openPositionRows().filter({ hasText: 'Invalidazione' })).toContainText(
      invalidation,
    );
  },
);

Then(
  'la decisione su {string} mostra obiettivo {int} e stop {int}',
  async ({ dashboard }, asset: string, target: number, stop: number) => {
    const plan = dashboard.page.getByRole('group', { name: `Piano di uscita di ${asset}` });
    await expect(plan).toContainText(`Obiettivo${formatPrice(String(target))}`);
    await expect(plan).toContainText(`Stop${formatPrice(String(stop))}`);
  },
);
