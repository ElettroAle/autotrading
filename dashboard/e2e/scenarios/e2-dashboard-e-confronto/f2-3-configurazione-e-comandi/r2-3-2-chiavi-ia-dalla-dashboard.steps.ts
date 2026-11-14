import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const PROVIDER_KEYS_TITLE = 'Chiavi dei fornitori IA';
const FIRST_KEY = 'chiave-prima';
const NEW_KEY = 'chiave-nuova';
// A registration of some days before: the replacement of the scenario is surely at another instant.
const EARLIER_REGISTRATION = '2026-11-01T08:00:00.000Z';

// The user acting in a step is the one the background signed in on the page of the keys.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

const registrationInstant = (dashboard: DashboardPages, provider: string) =>
  dashboard.providerKey(provider).getByLabel('Data di registrazione');

const savedInstantOf = (memory: ScenarioMemory, provider: string): string => {
  const key = fakePlatform.providerKeyOf(memory.account, provider);
  expect(key).toBeDefined();
  return key?.registeredAt ?? '';
};

Given(
  'che {string} è nella pagina delle chiavi IA',
  async ({ dashboard, memory }, account: string) => {
    memory.account = account;
    fakePlatform.addUser(account, { hasUserRole: true });
    await dashboard.openProviderKeys();
    await dashboard.signInAs(account);
    await expect(dashboard.pageHeading()).toHaveText(PROVIDER_KEYS_TITLE);
  },
);

Given(
  'che {string} ha una chiave per {string}',
  async ({ dashboard, memory }, account: string, provider: string) => {
    memory.registeredAt = fakePlatform.saveProviderKey(
      account,
      provider,
      EARLIER_REGISTRATION,
    ).registeredAt;
    memory.subject = provider;
    await dashboard.openProviderKeys();
    await expect(registrationInstant(dashboard, provider)).toHaveAttribute(
      'datetime',
      EARLIER_REGISTRATION,
    );
  },
);

When(
  '{string} registra una chiave per {string}',
  async ({ dashboard, memory }, account: string, provider: string) => {
    expectSignedIn(memory, account);
    memory.secret = FIRST_KEY;
    const form = dashboard.page.getByRole('region', { name: 'Nuova chiave' });
    await dashboard.field('Fornitore', form).fill(provider);
    await dashboard.field('Chiave', form).fill(FIRST_KEY);
    await form.getByRole('button', { name: 'Registra la chiave' }).click();
  },
);

When('{string} la sostituisce', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  memory.secret = NEW_KEY;
  const item = dashboard.providerKey(memory.subject);
  await item.getByRole('button', { name: 'Sostituisci la chiave' }).click();
  await dashboard.field('Nuova chiave', item).fill(NEW_KEY);
  await item.getByRole('button', { name: 'Sostituisci', exact: true }).click();
});

When('{string} la rimuove e conferma', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.providerKey(memory.subject).getByRole('button', { name: 'Rimuovi' }).click();
  await dashboard
    .confirmation(`Rimozione della chiave di ${memory.subject}`)
    .getByRole('button', { name: 'Conferma la rimozione' })
    .click();
});

Then(
  "l'elenco mostra {string} con la data di registrazione",
  async ({ dashboard, memory }, provider: string) => {
    await expect(registrationInstant(dashboard, provider)).toHaveAttribute(
      'datetime',
      savedInstantOf(memory, provider),
    );
  },
);

Then("l'elenco mostra la nuova data di registrazione", async ({ dashboard, memory }) => {
  await expect(registrationInstant(dashboard, memory.subject)).not.toHaveAttribute(
    'datetime',
    memory.registeredAt,
  );
  await expect(registrationInstant(dashboard, memory.subject)).toHaveAttribute(
    'datetime',
    savedInstantOf(memory, memory.subject),
  );
});

Then("{string} non compare più nell'elenco", async ({ dashboard, memory }, provider: string) => {
  await expect(dashboard.providerKey(provider)).toHaveCount(0);
  expect(fakePlatform.providerKeyOf(memory.account, provider)).toBeUndefined();
});
