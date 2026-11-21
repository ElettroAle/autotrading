import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';
import { formatAmount, formatSignedAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import { Given, Then, When } from '../../../support/fixtures';

const LAST_CLOSE = new Date('2026-11-14T09:00:00Z');
const HOUR = 3_600_000;

// A price averaged over several fills reaches the API with every digit of the division: the page rounds it (Bug 431,
// ADR formato-dei-prezzi-condiviso).
const averagedOverFills = (price: string): string => `${price}.0032258064516129032258064516`;

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
      openPrice: averagedOverFills(openPrice),
      closePrice: averagedOverFills(closePrice),
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
    await expect(dashboard.cell(first, 'PnL')).toHaveText(`PnL${formatSignedAmount(pnl)} USDC`);
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

Then(
  'la prima riga mostra direzione {word}, gli istanti di apertura e di chiusura, commissioni {amount} USDC e motivo {string}',
  async ({ dashboard }, side: string, fees: string, reason: string) => {
    const first = dashboard.closedPositionRows().first();
    const openedAt = new Date(LAST_CLOSE.getTime() - HOUR).toISOString();
    await expect(dashboard.cell(first, 'Direzione')).toContainText(side);
    await expect(dashboard.cell(first, 'Aperta il')).toHaveText(
      `Aperta il${formatInstant(openedAt)}`,
    );
    await expect(dashboard.cell(first, 'Chiusa il')).toHaveText(
      `Chiusa il${formatInstant(LAST_CLOSE.toISOString())}`,
    );
    await expect(dashboard.cell(first, 'Commissioni')).toHaveText(
      `Commissioni${formatAmount(fees)} USDC`,
    );
    await expect(dashboard.cell(first, 'Motivo')).toHaveText(`Motivo${reason}`);
  },
);

// The currency comes with the state of the flow, read on the exchange: without it the amounts have no unit (Bug 246).
Given(
  "che l'exchange del conto del flusso {string} non risponde",
  async ({ page }, flow: string) => {
    // The flow is the only one of the scenario, and it is given to the user only when she opens it.
    expect(flow).toBe('alfa');
    await page.route('**/flows/*/state*', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/problem+json',
        body: JSON.stringify({
          title: 'Service Unavailable',
          status: 503,
          detail: 'exchange non raggiungibile',
        }),
      }),
    );
  },
);

Then(
  'la prima riga mostra PnL {amount} e commissioni {amount} senza valuta',
  async ({ dashboard }, pnl: string, fees: string) => {
    const first = dashboard.closedPositionRows().first();
    await expect(dashboard.cell(first, 'PnL')).toHaveText(`PnL${formatSignedAmount(pnl)}`);
    await expect(dashboard.cell(first, 'Commissioni')).toHaveText(
      `Commissioni${formatAmount(fees)}`,
    );
  },
);
