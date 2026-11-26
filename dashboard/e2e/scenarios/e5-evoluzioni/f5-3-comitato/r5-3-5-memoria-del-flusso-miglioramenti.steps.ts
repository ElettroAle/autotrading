import { expect, type Locator } from '@playwright/test';

import type { FakeAssetMemory } from '@/testing/mocks/cycles';
import { configurationOf, DEFAULT_MEMORY, fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// The memory with the motive of every decision, the invalidation of an opening and how and after how long its position
// closed, and the length and the choice of the decisions in the form of the flow (R5.3.5, ADR
// memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni): the worker composes it, the dashboard reads it.

const USER = 'anna';
const MEMORY_TITLE = "Memoria dell'agente";
const MOTIVE = 'rottura della resistenza con volumi in aumento';
const INVALIDATION = 'chiusura sotto 0.0024';
const STOP_LOSS = 'chiusa dallo stop loss dopo 12 minuti';
const MEMORY: FakeAssetMemory[] = [
  {
    asset: 'DOGE',
    summary: [],
    other_assets: [],
    entries: [
      {
        planned_at: '2026-11-24T09:00:00Z',
        asset: 'DOGE',
        action: 'apri',
        direction: 'long',
        price: '0.002452',
        motive: MOTIVE,
        invalidation: INVALIDATION,
        outcome: { pnl: '-2.32', realized: true, course: STOP_LOSS },
      },
    ],
  },
];
const SAVE = 'Salva le modifiche';

const memoryOf = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('group', { name: MEMORY_TITLE });

Given(
  "che il flusso {string} ha la memoria attiva con una posizione chiusa dallo stop loss 12 minuti dopo l'apertura",
  async ({ memory }, flow: string) => {
    fakePlatform.ensureUser(USER);
    fakePlatform.addFlow(USER, flow, {
      memory: { ...DEFAULT_MEMORY, active: true },
      remembered: MEMORY,
    });
    memory.flow = flow;
  },
);

When(
  '{string} apre la memoria nelle decisioni di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openDecisionsAs(account, flow);
    await memoryOf(dashboard).getByText(MEMORY_TITLE).click();
  },
);

Then(
  "vede l'apertura con {string} e il suo PnL realizzato",
  async ({ dashboard }, course: string) => {
    await expect(memoryOf(dashboard).getByRole('table', { name: 'Memoria di DOGE' })).toContainText(
      `${course}, -2,32 realizzato`,
    );
  },
);

Then("vede il motivo e l'invalidazione dell'apertura", async ({ dashboard }) => {
  const table = memoryOf(dashboard).getByRole('table', { name: 'Memoria di DOGE' });
  await expect(table).toContainText(MOTIVE);
  await expect(table).toContainText(INVALIDATION);
});

When(
  '{string} sceglie per {string} la lunghezza «illimitata» e accende «tutte le decisioni»',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    const memory = dashboard.page.getByRole('group', { name: 'Memoria' });
    await memory.getByRole('checkbox', { name: 'Lunghezza illimitata' }).check();
    await memory.getByRole('checkbox', { name: 'Tutte le decisioni' }).check();
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(
  '{string} ha la memoria con lunghezza illimitata e «tutte le decisioni» accesa',
  async ({}, flow: string) => {
    expect(configurationOf(fakePlatform.flowNamed(flow)).memory).toMatchObject({
      active: true,
      text_length: null,
      all_decisions: true,
    });
  },
);
