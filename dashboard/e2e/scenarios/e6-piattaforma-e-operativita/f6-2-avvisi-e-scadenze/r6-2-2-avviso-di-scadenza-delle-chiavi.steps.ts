import { expect, type Locator } from '@playwright/test';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { fakeSourceCredentials } from '@/testing/mocks/source-credentials';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

const ACCOUNT_NAME = 'principale';
const REGISTERED_AT = '2026-11-14T09:00:00+00:00';
// The day the scenario runs on: the dates of the scenario are within or beyond 30 days of it as the scenario says.
const TODAY = new Date('2026-11-15T06:00:00Z');
const WALLET_VALID_UNTIL = '2026-12-30';
const SOURCE_ADAPTER = 'LunarCrush';

const expiryOf = (place: Locator): Locator => place.getByLabel('Scadenza della chiave');

// Every scenario opens one page, the first time the user comes to the dashboard.
const openAs = async (dashboard: DashboardPages, path: string, account: string) => {
  await dashboard.open(path);
  await dashboard.signInAs(account);
  await dashboard.waitUntilRead();
};

const keyItem = (dashboard: DashboardPages, provider: string): Locator =>
  dashboard.page.getByRole('listitem', { name: provider, exact: true });

Given(
  'che {string} ha la chiave del fornitore IA {string} usata dai flussi {string} e {string}',
  async ({ memory }, account: string, provider: string, first: string, second: string) => {
    fakeClock.fix(TODAY);
    fakePlatform.giveAccountTo(account, ACCOUNT_NAME, 500);
    fakePlatform.saveProviderKey(account, provider, REGISTERED_AT);
    for (const flow of [first, second]) {
      fakePlatform.addFlow(account, flow, {
        accountName: ACCOUNT_NAME,
        model: `${provider}/openai/gpt-4o`,
      });
    }
    memory.account = account;
  },
);

Given(
  'che {string} ha un conto {string} il cui API wallet è valido fino al 30 dicembre 2026',
  async ({ memory }, account: string, exchange: string) => {
    expect(account).toBe(memory.account);
    expect(exchange).toBe('Hyperliquid');
    expect(fakePlatform.accountNamed(ACCOUNT_NAME).expiry).toBeUndefined();
  },
);

// The exchange gives the validity of the API wallet at every verification of the credentials (R6.2.2).
When('la piattaforma verifica le credenziali del conto', async () => {
  fakePlatform.accountNamed(ACCOUNT_NAME).expiry = {
    expiresOn: WALLET_VALID_UNTIL,
    source: 'read',
  };
});

Then('il conto mostra la scadenza 30 dicembre 2026', async ({ dashboard, memory }) => {
  await openAs(dashboard, '/accounts', memory.account);
  const account = dashboard.page.getByRole('article', { name: ACCOUNT_NAME });
  await expect(expiryOf(account)).toHaveText("scade il 30/12/2026 · letta dall'exchange");
});

When(
  '{string} indica per la chiave {string} la scadenza 15 dicembre 2026',
  async ({ dashboard }, account: string, provider: string) => {
    await openAs(dashboard, '/provider-keys', account);
    const item = keyItem(dashboard, provider);
    await item.getByRole('button', { name: 'Indica scadenza' }).click();
    await item.getByLabel('Scadenza', { exact: true }).fill('2026-12-15');
    await item.getByRole('button', { name: 'Salva la scadenza' }).click();
    await expect(item.getByLabel('Scadenza', { exact: true })).toHaveCount(0);
  },
);

Then('la chiave mostra la scadenza 15 dicembre 2026', async ({ dashboard }) => {
  const item = keyItem(dashboard, 'openrouter');
  await expect(expiryOf(item)).toHaveText('scade tra 30 giorni · 15/12/2026');
});

// The credentials of an adapter of a source, saved without a date (R4.1.2).
Given('che la chiave di un adapter di fonte non ha una data di scadenza', async ({ memory }) => {
  fakeSourceCredentials.offerAdapter('sentiment', SOURCE_ADAPTER);
  fakeSourceCredentials.configure(memory.account, SOURCE_ADAPTER, { api_key: 'K' }, REGISTERED_AT);
  expect(fakeSourceCredentials.of(memory.account, SOURCE_ADAPTER)?.expiry).toBeUndefined();
});

When('{string} apre la pagina Chiavi', async ({ dashboard, memory }, account: string) => {
  expect(account).toBe(memory.account);
  await openAs(dashboard, '/provider-keys', account);
});

Then('la chiave mostra {string} e non genera avvisi', async ({ dashboard }, state: string) => {
  const item = dashboard.page
    .getByRole('region', { name: 'Fonti' })
    .getByRole('listitem', { name: SOURCE_ADAPTER, exact: true });
  await expect(expiryOf(item)).toHaveText(state);
  await expect(dashboard.page.getByRole('region', { name: 'Chiavi da rinnovare' })).toHaveCount(0);
});
