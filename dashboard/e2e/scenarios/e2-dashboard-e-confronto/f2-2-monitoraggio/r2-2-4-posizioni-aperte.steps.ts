import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { formatAmount, formatSignedAmount } from '@/utils/format-amount';

import { Given, Then, When } from '../../../support/fixtures';

Given(
  'che il flusso {string} ha una posizione {word} su {string} con leva {int}, dimensione {amount}, prezzo di ingresso {amount} e PnL corrente {amount} USDC',
  async (
    {},
    flow: string,
    side: string,
    asset: string,
    leverage: number,
    size: string,
    entryPrice: string,
    pnl: string,
  ) => {
    fakePlatform.holdPositions(flow, [
      anOpenPosition({ asset, side, size, leverage: String(leverage), entryPrice, pnl }),
    ]);
  },
);

Given('che il flusso {string} non ha posizioni aperte', async ({}, flow: string) => {
  fakePlatform.holdPositions(flow, []);
});

When(
  '{string} apre le posizioni del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    fakePlatform.giveFlowTo(account, flow);
    await dashboard.openPositionsOf(flow);
    await dashboard.signInAs(account);
  },
);

Then(
  'vede {string} {word}, leva {int}, dimensione {amount}, ingresso {amount}, PnL {amount} USDC',
  async (
    { dashboard },
    asset: string,
    side: string,
    leverage: number,
    size: string,
    entryPrice: string,
    pnl: string,
  ) => {
    const row = dashboard.openPositionRows().filter({ hasText: asset });
    await expect(dashboard.cell(row, 'Asset')).toContainText(asset);
    await expect(dashboard.cell(row, 'Direzione')).toContainText(side);
    await expect(dashboard.cell(row, 'Leva')).toHaveText(`Leva${leverage}`);
    await expect(dashboard.cell(row, 'Dimensione')).toContainText(formatAmount(size));
    await expect(dashboard.cell(row, 'Prezzo di ingresso')).toContainText(formatAmount(entryPrice));
    await expect(dashboard.cell(row, 'PnL')).toContainText(`${formatSignedAmount(pnl)} USDC`);
  },
);
