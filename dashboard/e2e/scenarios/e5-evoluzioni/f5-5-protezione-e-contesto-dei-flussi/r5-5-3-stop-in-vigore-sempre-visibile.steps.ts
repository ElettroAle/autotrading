import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { formatPrice } from '@/utils/format-amount';

import { Given, Then, When } from '../../../support/fixtures';

// The stop the platform placed on the exchange for the position, whatever its origin, is what the API gives in the state
// of the flow (R5.5.3, ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione): the dashboard shows it, never
// computes it. The fake API answers the stop of a position opened without an exit plan as the platform placed it: the
// default stop loss of the flow on the entry price.
const defaultStopOf = (entryPrice: number, defaultStopLossPercent: number): string =>
  String((entryPrice * (100 - defaultStopLossPercent)) / 100);

Given(
  'che {string} ha il flusso {string} attivo con asset {string} e stop loss predefinito {int}%',
  async ({ memory }, account: string, flow: string, asset: string, stopLoss: number) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, {
      assets: [asset],
      defaultStopLossPercent: String(stopLoss),
    });
    memory.account = account;
    memory.flow = flow;
  },
);

Given(
  "che {string} ha aperto long su {string} al prezzo d'ingresso {int} senza piano di uscita",
  async ({ memory }, flow: string, asset: string, entryPrice: number) => {
    memory.flow = flow;
    const stopLoss = Number(fakePlatform.flowNamed(flow).defaultStopLossPercent);
    fakePlatform.holdPositions(flow, [
      anOpenPosition({
        asset,
        side: 'long',
        entryPrice: String(entryPrice),
        stop: defaultStopOf(entryPrice, stopLoss),
      }),
    ]);
  },
);

When(
  '{string} apre le posizioni di {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openPositionsOf(flow);
    await dashboard.signInAs(account);
  },
);

Then(
  'la posizione su {string} mostra stop {int}',
  async ({ dashboard }, asset: string, stop: number) => {
    const row = dashboard.openPositionRows().filter({ hasText: asset });
    await expect(dashboard.cell(row, 'Stop')).toHaveText(`Stop${formatPrice(String(stop))}`);
  },
);
