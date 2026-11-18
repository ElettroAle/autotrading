import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then } from '../../../support/fixtures';

// The balance says it holds the result of the open positions; the capital allocated is shown under the value of the
// flows, in the currency of that value (Bug 601, ADR scomposizione-del-saldo-nel-riquadro-del-conto). The list shows
// balance and free capital; the breakdown is on the overview of the page of the account (ADR
// elenco-dei-conti-e-pagina-del-conto).
const BALANCE = 'Saldo (con risultato aperto)';
const ALLOCATED = 'capitale allocato';

const expectShown = async (value: Locator, text: string): Promise<void> => {
  await expect(value).toHaveText(text, { useInnerText: true });
};

Given(
  'che {string} ha il conto {string} su testnet con saldo {int} USDC',
  async ({ memory }, account: string, name: string, balance: number) => {
    fakePlatform.giveAccountTo(account, name, balance);
    memory.account = account;
  },
);

Given(
  'che i flussi {string} e {string} hanno allocato {int} e {int} USDC sul conto {string}',
  async ({ memory }, first: string, second: string, one: number, other: number, name: string) => {
    fakePlatform.addFlow(memory.account, first, { accountName: name, allocatedCapital: one });
    fakePlatform.addFlow(memory.account, second, { accountName: name, allocatedCapital: other });
  },
);

Given('che {string} non ha conti', async ({}, account: string) => {
  fakePlatform.addUser(account, { hasUserRole: true });
});

Given("che l'exchange non risponde", async () => {
  fakePlatform.stopExchange();
});

Then(
  'il conto {string} mostra ambiente {string}, saldo {int} USDC, capitale allocato {int} USDC e capitale libero {int} USDC',
  async (
    { dashboard },
    name: string,
    network: string,
    balance: number,
    allocated: number,
    free: number,
  ) => {
    // The network carries its kind beside the name the exchange gives it (R2.3.10).
    await expectShown(dashboard.accountNetwork(name), `TEST · ${network}`);
    await expectShown(dashboard.accountItemDetail(name, BALANCE), `${balance} USDC`);
    await expectShown(dashboard.accountItemDetail(name, 'Capitale libero'), `${free} USDC`);
    await dashboard.openAccount(name);
    await expectShown(dashboard.accountPageDetail(ALLOCATED), String(allocated));
  },
);

Then(
  'la pagina mostra {string} e il comando per registrarne uno',
  async ({ dashboard }, message: string) => {
    await expect(dashboard.page.getByText(message)).toBeVisible();
    await expect(dashboard.registerAccount()).toBeVisible();
  },
);

Then(
  'il conto {string} mostra {string} al posto del saldo',
  async ({ dashboard, memory }, name: string, message: string) => {
    memory.tradingAccount = name;
    await expectShown(dashboard.accountItemDetail(name, BALANCE), message);
  },
);

Then('mostra il capitale allocato {int} USDC', async ({ dashboard, memory }, allocated: number) => {
  await dashboard.openAccount(memory.tradingAccount);
  await expectShown(dashboard.accountPageDetail(ALLOCATED), String(allocated));
});
