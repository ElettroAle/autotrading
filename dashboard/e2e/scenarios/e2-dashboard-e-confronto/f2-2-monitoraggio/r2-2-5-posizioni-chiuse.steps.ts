import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';
import { formatAmount, formatSignedAmount } from '@/utils/format-amount';

import { Given, Then, When } from '../../../support/fixtures';

const LAST_CLOSE = new Date('2026-11-14T09:00:00Z');
const HOUR = 3_600_000;

// The margin of the last position, at leverage 1, is the value whose price move gave its PnL: the API measures the
// percent on it.
const marginOf = (side: string, openPrice: string, closePrice: string, pnl: string): string => {
  const move = (Number(closePrice) - Number(openPrice)) / Number(openPrice);
  return String(Number(pnl) / (side === 'long' ? move : -move));
};

Given(
  "che il flusso {string} ha {int} posizioni chiuse, l'ultima {word} su {string} aperta a {amount} e chiusa a {amount} con PnL {amount} USDC",
  async (
    {},
    flow: string,
    count: number,
    side: string,
    asset: string,
    openPrice: string,
    closePrice: string,
    pnl: string,
  ) => {
    const earlier = Array.from({ length: count - 1 }, (_, index) =>
      aClosedPosition({ closedAt: new Date(LAST_CLOSE.getTime() - (index + 1) * HOUR) }),
    );
    const last = aClosedPosition({
      closedAt: LAST_CLOSE,
      asset,
      side,
      openPrice,
      closePrice,
      pnl,
      margin: marginOf(side, openPrice, closePrice, pnl),
    });
    fakePlatform.recordClosedPositions(flow, [...earlier, last]);
  },
);

When(
  '{string} apre le posizioni chiuse del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    fakePlatform.giveFlowTo(account, flow);
    await dashboard.openClosedPositionsOf(flow);
    await dashboard.signInAs(account);
  },
);

Then(
  'la prima riga è {string} con apertura {amount}, chiusura {amount}, PnL {amount} USDC e {percent}',
  async (
    { dashboard },
    asset: string,
    openPrice: string,
    closePrice: string,
    pnl: string,
    percent: string,
  ) => {
    const first = dashboard.closedPositionRows().first();
    await expect(dashboard.cell(first, 'Asset')).toHaveText(`Asset${asset}`);
    await expect(dashboard.cell(first, 'Apertura')).toHaveText(
      `Apertura${formatAmount(openPrice)}`,
    );
    await expect(dashboard.cell(first, 'Chiusura')).toHaveText(
      `Chiusura${formatAmount(closePrice)}`,
    );
    await expect(dashboard.cell(first, 'PnL')).toHaveText(`PnL${formatSignedAmount(pnl)}`);
    await expect(dashboard.cell(first, 'PnL %')).toHaveText(`PnL %${percent}`);
  },
);

Then(
  'la pagina mostra {int} posizioni con il comando per la pagina successiva',
  async ({ dashboard }, count: number) => {
    await expect(dashboard.closedPositionRows()).toHaveCount(count);
    await expect(dashboard.nextPage()).toBeVisible();
  },
);
