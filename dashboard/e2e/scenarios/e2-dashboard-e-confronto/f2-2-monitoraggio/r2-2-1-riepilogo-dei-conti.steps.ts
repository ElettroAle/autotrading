import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The header of each cell stays in the page for narrow screens, hidden on the wide one: the text is what shows.
const expectShown = async (cell: Promise<Locator>, text: string): Promise<void> => {
  await expect(await cell).toHaveText(text, { useInnerText: true });
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

When('{string} apre la pagina dei conti', async ({ dashboard }, account: string) => {
  await dashboard.openAccounts();
  await dashboard.signInAs(account);
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
    await expectShown(dashboard.accountCell(name, 'Rete'), network);
    await expectShown(dashboard.accountCell(name, 'Saldo'), `${balance} USDC`);
    await expectShown(dashboard.accountCell(name, 'Capitale allocato'), `${allocated} USDC`);
    await expectShown(dashboard.accountCell(name, 'Capitale libero'), `${free} USDC`);
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
    await expectShown(dashboard.accountCell(name, 'Saldo'), message);
  },
);

Then('mostra il capitale allocato {int} USDC', async ({ dashboard, memory }, allocated: number) => {
  await expectShown(
    dashboard.accountCell(memory.tradingAccount, 'Capitale allocato'),
    `${allocated} USDC`,
  );
});
