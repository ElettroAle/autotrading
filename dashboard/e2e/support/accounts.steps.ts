import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, When } from './fixtures';

// Shared by the summary of the accounts (R2.2.1) and the state of their reconciliation (R3.3.2).
When('{string} apre la pagina dei conti', async ({ dashboard }, account: string) => {
  await dashboard.openAccounts();
  await dashboard.signInAs(account);
});

// Shared by the info of the settings of the account (R5.5.7) and its reconciliation interval (Bug 778): the account is
// given to the user when the scenario has not given it yet, and she signs in unless a step before already did.
Given(
  'che {string} ha aperto la pagina del conto {string}',
  async ({ dashboard, memory }, account: string, name: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addAccount(account, name);
    await dashboard.openAccounts();
    if (memory.account !== account) {
      await dashboard.signInAs(account);
      memory.account = account;
    }
    await dashboard.openAccount(name, 'Impostazioni');
    // The credentials are asked only once the user chooses to replace them: their fields are settings too.
    await dashboard.content().getByRole('button', { name: 'Sostituisci le credenziali' }).click();
    await expect(
      dashboard.content().getByRole('form', { name: `Nuove credenziali del conto ${name}` }),
    ).toBeVisible();
  },
);
