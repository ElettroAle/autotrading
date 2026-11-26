import { expect } from '@playwright/test';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The block of the reopenings after consecutive losses in the form of the flow, and the blocks in force on its page
// (R5.5.2, ADR blocco-delle-riaperture-nella-dashboard): the API checks the settings and computes the blocks from the
// closings, the dashboard sends what the user types and shows the text the API gives.

const SAVE = 'Salva le modifiche';

When(
  /^"([^"]+)" imposta nel modulo di "([^"]+)" perdite consecutive massime (\d+), finestra (\d+) ore e durata del blocco (\d+) minuti$/,
  async (
    { dashboard },
    account: string,
    flow: string,
    losses: number,
    hours: number,
    minutes: number,
  ) => {
    // The scenario names no flow beforehand: the user edits one of hers.
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow);
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    const page = dashboard.page;
    await page.getByLabel('Perdite consecutive massime', { exact: true }).fill(String(losses));
    await page.getByLabel('Finestra delle perdite (ore)', { exact: true }).fill(String(hours));
    await page.getByLabel('Durata del blocco (minuti)', { exact: true }).fill(String(minutes));
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(
  /^"([^"]+)" ha perdite consecutive massime (\d+), finestra (\d+) ore e durata del blocco (\d+) minuti$/,
  async ({}, flow: string, losses: number, hours: number, minutes: number) => {
    expect(configurationOf(fakePlatform.flowNamed(flow)).consecutive_loss_limit).toEqual({
      max_consecutive_losses: losses,
      loss_window_hours: hours,
      block_minutes: minutes,
      count_scope: 'asset',
    });
  },
);

Given(
  'che {string} ha le riaperture short su {string} ferme fino alle 15:30',
  async ({ memory }, flow: string, asset: string) => {
    fakePlatform.ensureUser('anna');
    fakePlatform.addFlow('anna', flow, {
      assets: [asset],
      consecutiveLossLimit: {
        max_consecutive_losses: 2,
        loss_window_hours: 24,
        block_minutes: 120,
        count_scope: 'asset',
      },
      // The block as the API reads it from two losses at 13:00 and 13:30, with the text of its domain.
      reopeningBlocks: [
        {
          side: 'short',
          asset,
          consecutive_losses: 2,
          until: '2026-11-26T15:30:00Z',
          text: `riaperture short su ${asset} ferme fino alle 15:30: 2 perdite consecutive`,
        },
      ],
    });
    memory.flow = flow;
  },
);

// The instant of the opening is the one the API reads the blocks at: the page shows what the API gives.
When(
  'alle 14:00 {string} apre la pagina di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
  },
);
