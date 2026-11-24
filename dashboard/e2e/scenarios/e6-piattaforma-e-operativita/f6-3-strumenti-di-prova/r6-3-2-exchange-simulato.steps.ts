import { expect, type Locator } from '@playwright/test';

import { SIMULATED_EXCHANGE, fakePlatform } from '@/testing/mocks/platform';
import { formatAmount } from '@/utils/format-amount';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// The execution on the real market, the rules of the market and the isolation of the tenants have no step here:
// pytest-bdd runs them on the use cases of the api and of the worker (ADR 0116).

const ACCOUNT_FORM = 'Nuovo conto';
const ACCOUNT_NAME = 'prova';
const RESET = 'Azzera il conto';

const form = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('region', { name: ACCOUNT_FORM });

const virtualBalanceOf = (dashboard: DashboardPages, account: string): Locator =>
  dashboard.content().getByRole('region', { name: `Saldo virtuale del conto ${account}` });

When(
  "{string} registra un conto scegliendo l'exchange {string}",
  async ({ dashboard, memory }, account: string, exchange: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.offerSimulatedExchange();
    memory.account = account;
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    const region = form(dashboard);
    await region.getByLabel('Nome').fill(ACCOUNT_NAME);
    await expect(region.locator(`option[value="${exchange}"]`)).toBeEnabled();
    await dashboard.field('Exchange', region).selectOption(exchange);
  },
);

Then('il modulo non chiede credenziali ma il saldo virtuale', async ({ dashboard }) => {
  const region = form(dashboard);
  await expect(region.getByLabel('Saldo virtuale')).toBeVisible();
  await expect(region.getByLabel('Indirizzo del conto')).toHaveCount(0);
  await expect(region.getByLabel("Chiave dell'API wallet")).toHaveCount(0);
});

Then("il conto mostra l'avviso della rete {string}", async ({ dashboard }, network: string) => {
  await expect(form(dashboard).getByRole('note')).toHaveText(
    `Il conto opererà sulla rete di test "${network}", senza denaro reale`,
  );
});

Given(
  'che {string} ha un conto {string} con saldo virtuale {int} USDC',
  async ({ memory }, account: string, exchange: string, balance: number) => {
    expect(exchange).toBe(SIMULATED_EXCHANGE);
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addSimulatedAccount(account, ACCOUNT_NAME, balance);
    memory.account = account;
  },
);

When(
  '{string} azzera il conto dalla sua pagina con saldo {int} USDC',
  async ({ dashboard }, account: string, balance: number) => {
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    await dashboard.openAccount(ACCOUNT_NAME, 'Impostazioni');
    const region = virtualBalanceOf(dashboard, ACCOUNT_NAME);
    await region.getByLabel('Nuovo saldo virtuale (USDC)').fill(String(balance));
    await region.getByRole('button', { name: RESET }).click();
    await region.getByRole('alertdialog').getByRole('button', { name: RESET }).click();
    await expect(region.getByRole('status')).toHaveText(
      `Conto ${ACCOUNT_NAME} azzerato con saldo ${balance} USDC`,
    );
  },
);

Then('la pagina del conto mostra saldo {int} USDC', async ({ dashboard }, balance: number) => {
  await dashboard.openAccount(ACCOUNT_NAME);
  await expect(dashboard.accountPageDetail('Saldo (con risultato aperto)')).toContainText(
    `${formatAmount(String(balance))} USDC`,
  );
});
