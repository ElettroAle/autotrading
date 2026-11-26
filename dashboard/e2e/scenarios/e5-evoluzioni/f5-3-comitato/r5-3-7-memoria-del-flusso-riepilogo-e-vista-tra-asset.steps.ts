import { expect } from '@playwright/test';

import { configurationOf, DEFAULT_MEMORY, fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The summary and the other assets of the memory in the form of the flow, and the summary lines before the decisions of
// an asset in the memory shown, with the text of the API (R5.3.7, ADR opzioni-della-memoria-nella-dashboard): the
// worker composes them, the dashboard reads them.

const USER = 'anna';
const MEMORY_TITLE = "Memoria dell'agente";
const SAVE = 'Salva le modifiche';
const summaryLineOf = (asset: string): string =>
  `${asset} short — oggi: 2 chiuse, 0 vinte, 2 perse, PnL -4,80 USDC; ultimi 30 giorni: 2 chiuse, 0 vinte, 2 perse, PnL -4,80 USDC`;

Given(
  'che il flusso {string} ha la memoria attiva con il riepilogo acceso e posizioni short chiuse oggi su {string}',
  async ({ memory }, flow: string, asset: string) => {
    fakePlatform.ensureUser(USER);
    fakePlatform.addFlow(USER, flow, {
      memory: { ...DEFAULT_MEMORY, active: true, summary: true },
      remembered: [{ asset, summary: [summaryLineOf(asset)], other_assets: [], entries: [] }],
    });
    memory.flow = flow;
  },
);

When(
  '{string} accende per {string} il riepilogo e gli altri asset',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    const memory = dashboard.page.getByRole('group', { name: 'Memoria' });
    await memory.getByRole('checkbox', { name: 'Riepilogo per asset e direzione' }).check();
    await memory.getByRole('checkbox', { name: 'Altri asset del flusso' }).check();
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(
  '{string} ha la memoria con il riepilogo acceso e gli altri asset accesi',
  async ({}, flow: string) => {
    expect(configurationOf(fakePlatform.flowNamed(flow)).memory).toMatchObject({
      active: true,
      summary: true,
      other_assets: true,
    });
  },
);

Then(
  'vede in testa alla memoria di {string} la riga di riepilogo short',
  async ({ dashboard }, asset: string) => {
    const memory = dashboard.page.getByRole('group', { name: MEMORY_TITLE });
    const summary = memory.getByRole('list', { name: `Riepilogo di ${asset}` });
    await expect(summary).toHaveText(summaryLineOf(asset));
    await expect(summary.getByRole('listitem').first()).toHaveText(
      new RegExp(`^${asset} short — `),
    );
  },
);
