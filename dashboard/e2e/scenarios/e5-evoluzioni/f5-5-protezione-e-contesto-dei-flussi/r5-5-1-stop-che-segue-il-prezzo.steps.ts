import { expect } from '@playwright/test';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { formatAmount, formatPrice } from '@/utils/format-amount';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// The stop that follows the price in the form of the flow, and the largest profit a position reached in its view
// (R5.5.1, ADR stop-che-segue-il-prezzo-nella-dashboard): the API checks the settings and computes the profit, the
// dashboard sends what the user types and shows what the API gives.

const SAVE = 'Salva le modifiche';
const DISTANCE = 'Distanza dello stop che segue (%)';
const ACTIVATION = 'Attivazione (%)';
const BREAKEVEN = 'Pareggio (%)';

// The scenarios of the form name no flow beforehand: the user edits one of hers.
const editFlow = async (dashboard: DashboardPages, account: string, flow: string) => {
  fakePlatform.ensureUser(account);
  fakePlatform.addFlow(account, flow);
  await dashboard.openFlowEditor(flow);
  await dashboard.signInAs(account);
};

const typeIn = async (dashboard: DashboardPages, label: string, percent: string) => {
  await dashboard.page.getByLabel(label, { exact: true }).fill(percent);
};

When(
  /^"([^"]+)" imposta nel modulo di "([^"]+)" distanza dello stop che segue (\S+)%, attivazione (\S+)% e pareggio (\S+)%$/,
  async (
    { dashboard },
    account: string,
    flow: string,
    distance: string,
    activation: string,
    breakeven: string,
  ) => {
    await editFlow(dashboard, account, flow);
    await typeIn(dashboard, DISTANCE, distance);
    await typeIn(dashboard, ACTIVATION, activation);
    await typeIn(dashboard, BREAKEVEN, breakeven);
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(
  /^"([^"]+)" ha distanza dello stop che segue (\S+)%, attivazione (\S+)% e pareggio (\S+)%$/,
  async ({}, flow: string, distance: string, activation: string, breakeven: string) => {
    const decimal = (percent: string): string => percent.replace(',', '.');
    expect(configurationOf(fakePlatform.flowNamed(flow)).trailing_stop).toMatchObject({
      distance_percent: decimal(distance),
      activation_percent: decimal(activation),
      breakeven_percent: decimal(breakeven),
    });
  },
);

When(
  /^"([^"]+)" imposta nel modulo di "([^"]+)" l'attivazione (\S+)% senza distanza$/,
  async ({ dashboard }, account: string, flow: string, activation: string) => {
    await editFlow(dashboard, account, flow);
    await typeIn(dashboard, ACTIVATION, activation);
    await dashboard.button(SAVE).click();
  },
);

Then('il modulo mostra {string}', async ({ dashboard }, reason: string) => {
  await expect(dashboard.page.getByText(reason, { exact: true })).toBeVisible();
});

Given(
  'che {string} ha una posizione long su {string} con stop {int} e massimo profitto raggiunto {int} USDC',
  async ({ memory }, flow: string, asset: string, stop: number, maxProfit: number) => {
    fakePlatform.ensureUser('anna');
    fakePlatform.addFlow('anna', flow, {
      assets: [asset],
      trailingStop: {
        distance_percent: '2',
        activation_percent: null,
        breakeven_percent: null,
        max_profit_in_context: false,
      },
    });
    fakePlatform.holdPositions(flow, [
      anOpenPosition({
        asset,
        side: 'long',
        stop: String(stop),
        maxProfit: String(maxProfit),
      }),
    ]);
    memory.flow = flow;
  },
);

Then(
  'la posizione su {string} mostra stop {int} e massimo profitto raggiunto {int} USDC',
  async ({ dashboard }, asset: string, stop: number, maxProfit: number) => {
    const row = dashboard.openPositionRows().filter({ hasText: asset });
    await expect(dashboard.cell(row, 'Stop')).toHaveText(`Stop${formatPrice(String(stop))}`);
    await expect(dashboard.cell(row, 'Massimo profitto raggiunto')).toHaveText(
      `Massimo profitto raggiunto${formatAmount(String(maxProfit))} USDC`,
    );
  },
);
