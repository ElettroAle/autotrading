import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import {
  fakeSourceCredentials,
  notConfiguredReason,
  SOURCE_API_KEY_FIELD,
} from '@/testing/mocks/source-credentials';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The scenarios of what the worker does in a cycle (the credentials the provider refuses) have no step here: pytest-bdd
// runs them on the use cases (ADR 0116).
const KEYS_TITLE = 'Chiavi';
const SENTIMENT = 'sentiment';
const TRADING_ACCOUNT = 'principale';
const TYPED_KEY = 'K-LUNAR-SEGRETA';
const SAVED_AT = '2026-11-14T09:00:00.000Z';

const sourcesSection = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('region', { name: 'Fonti' });

const adapterItem = (dashboard: DashboardPages, adapter: string): Locator =>
  sourcesSection(dashboard).getByRole('listitem', { name: adapter, exact: true });

// The user acting in a step is the one the background signed in on the page of the keys.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

const configureAs = (account: string, adapter: string): void => {
  fakeSourceCredentials.configure(account, adapter, { api_key: TYPED_KEY }, SAVED_AT);
};

const openSourcesSection = async (dashboard: DashboardPages): Promise<void> => {
  await dashboard.openProviderKeys();
  await dashboard.waitUntilRead();
  await expect(sourcesSection(dashboard)).toBeVisible();
};

Given(
  'che {string} è nella pagina delle chiavi',
  async ({ dashboard, memory }, account: string) => {
    memory.account = account;
    fakePlatform.addUser(account, { hasUserRole: true });
    await dashboard.openProviderKeys();
    await dashboard.signInAs(account);
    await expect(dashboard.pageHeading()).toHaveText(KEYS_TITLE);
  },
);

Given(
  'che esiste un adapter di fonte {string} che richiede una {string} segreta',
  async ({ memory }, adapter: string, field: string) => {
    expect(field.toLowerCase()).toBe(SOURCE_API_KEY_FIELD.label.toLowerCase());
    fakeSourceCredentials.offerAdapter(SENTIMENT, adapter, [SOURCE_API_KEY_FIELD]);
    memory.subject = adapter;
  },
);

Given("che l'adapter {string} non è configurato", async ({ memory }, adapter: string) => {
  expect(fakeSourceCredentials.of(memory.account, adapter)).toBeUndefined();
});

Given(
  "che {string} ha configurato l'adapter {string}",
  async ({ memory }, account: string, adapter: string) => {
    expect(account).not.toBe(memory.account);
    fakePlatform.addUser(account, { hasUserRole: true });
    configureAs(account, adapter);
  },
);

When(
  "{string} inserisce la chiave API dell'adapter {string}",
  async ({ dashboard, memory }, account: string, adapter: string) => {
    expectSignedIn(memory, account);
    await openSourcesSection(dashboard);
    const item = adapterItem(dashboard, adapter);
    await item.getByRole('button', { name: 'Configura' }).click();
    await dashboard.field(SOURCE_API_KEY_FIELD.label, item).fill(TYPED_KEY);
    memory.secret = TYPED_KEY;
    await item.getByRole('button', { name: 'Salva le credenziali' }).click();
  },
);

When(
  '{string} prova ad attivarlo nel flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    expectSignedIn(memory, account);
    fakePlatform.giveAccountTo(account, TRADING_ACCOUNT, 500);
    fakePlatform.addFlow(account, flow, { accountName: TRADING_ACCOUNT });
    memory.refusal = notConfiguredReason(memory.subject);
    await dashboard.openFlowEditor(flow);
    await expect(dashboard.field('Nome')).toHaveValue(flow);
    await dashboard.page.getByRole('checkbox', { name: SENTIMENT, exact: true }).check();
  },
);

When(
  '{string} apre la sezione {string} delle chiavi',
  async ({ dashboard, memory }, account: string, section: string) => {
    expectSignedIn(memory, account);
    expect(section).toBe('Fonti');
    await openSourcesSection(dashboard);
  },
);

Then("l'adapter {string} risulta configurato", async ({ dashboard }, adapter: string) => {
  const item = adapterItem(dashboard, adapter);
  await expect(item.getByText('configurato', { exact: true })).toBeVisible();
  await expect(item.getByRole('button', { name: 'Sostituisci' })).toBeVisible();
});

// The same words as R2.3.9, where the key is that of an account: here it is that of an adapter of a source.
Then('la chiave non è mostrata in chiaro', { tags: '@R4.1.2' }, async ({ dashboard, memory }) => {
  await expect(sourcesSection(dashboard)).not.toContainText(memory.secret);
  await expect(dashboard.page.getByText(memory.secret)).toHaveCount(0);
  const item = adapterItem(dashboard, memory.subject);
  await item.getByRole('button', { name: 'Sostituisci' }).click();
  const secret = dashboard.field(SOURCE_API_KEY_FIELD.label, item);
  await expect(secret).toHaveAttribute('type', 'password');
  await expect(secret).toHaveValue('');
});

Then(
  "l'attivazione è rifiutata con il motivo {string}",
  async ({ dashboard, memory }, reason: string) => {
    expect(reason).toBe(memory.refusal);
    const adapters = dashboard.page.getByRole('list', { name: `Adapter di ${SENTIMENT}` });
    const paid = adapters.getByRole('checkbox', { name: memory.subject, exact: true });
    await expect(paid).toBeDisabled();
    await expect(paid).toHaveAccessibleDescription(new RegExp(`${reason}$`));
  },
);

Then(
  "l'adapter {string} non è elencato tra quelli da configurare",
  async ({ dashboard, memory }, adapter: string) => {
    await expect(adapterItem(dashboard, adapter)).toHaveCount(0);
    await expect(adapterItem(dashboard, memory.subject)).toBeVisible();
  },
);

Then(
  "l'adapter {string} risulta non configurato per {string}",
  async ({ dashboard, memory }, adapter: string, account: string) => {
    expectSignedIn(memory, account);
    const item = adapterItem(dashboard, adapter);
    await expect(item.getByText('non configurato', { exact: true })).toBeVisible();
    await expect(item.getByRole('button', { name: 'Configura' })).toBeVisible();
  },
);
