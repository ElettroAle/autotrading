import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { API_KEY_FIELD } from '@/testing/mocks/provider-key-handlers';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Then, When, type ScenarioMemory } from '../../../support/fixtures';

const ACCOUNT_FORM = 'Nuovo conto';
const PROVIDER_KEY_FORM = 'Nuova chiave';
const ADDRESS_LABEL = 'Indirizzo del conto';
const API_WALLET_KEY_LABEL = "Chiave dell'API wallet";
const VALID_ADDRESS = `0x${'a1'.repeat(20)}`;

const formOf = (dashboard: DashboardPages, name: string): Locator =>
  dashboard.page.getByRole('region', { name });

// The spec names a field as a sentence does: the form shows its label with the first letter capital.
const labelOf = (field: string): string => `${field.charAt(0).toUpperCase()}${field.slice(1)}`;

// The user acting in a step is the one the background signed in on the page of the accounts.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

Then(
  'la registrazione chiede {string} e {string}',
  async ({ dashboard }, first: string, second: string) => {
    const form = formOf(dashboard, ACCOUNT_FORM);
    await expect(dashboard.field(labelOf(first), form)).toBeVisible();
    await expect(dashboard.field(labelOf(second), form)).toBeVisible();
  },
);

Then('la chiave non è mostrata in chiaro', async ({ dashboard }) => {
  const form = formOf(dashboard, ACCOUNT_FORM);
  await expect(dashboard.field(API_WALLET_KEY_LABEL, form)).toHaveAttribute('type', 'password');
  await expect(dashboard.field(ADDRESS_LABEL, form)).not.toHaveAttribute('type', 'password');
});

When(
  "{string} registra un conto {string} senza la chiave dell'API wallet",
  async ({ dashboard, memory }, account: string, exchange: string) => {
    expectSignedIn(memory, account);
    const form = formOf(dashboard, ACCOUNT_FORM);
    await dashboard.field('Exchange', form).selectOption(exchange);
    await dashboard.field('Nome', form).fill('principale');
    await dashboard.field(ADDRESS_LABEL, form).fill(VALID_ADDRESS);
    await form.getByRole('button', { name: 'Registra il conto' }).click();
  },
);

Then(
  'la registrazione fallisce con il motivo {string}',
  async ({ dashboard, memory }, reason: string) => {
    const form = formOf(dashboard, ACCOUNT_FORM);
    await expect(dashboard.field(API_WALLET_KEY_LABEL, form)).toHaveAccessibleDescription(reason);
    expect(fakePlatform.user(memory.account).accounts).toEqual([]);
  },
);

When(
  '{string} sceglie il fornitore {string} per registrare una chiave',
  async ({ dashboard, memory }, account: string, provider: string) => {
    expectSignedIn(memory, account);
    await dashboard.openProviderKeys();
    const form = formOf(dashboard, PROVIDER_KEY_FORM);
    await dashboard.field('Fornitore', form).selectOption(provider);
    memory.subject = provider;
  },
);

Then(
  'la registrazione chiede i dati che {string} richiede',
  async ({ dashboard }, provider: string) => {
    expect(provider).toBe('openrouter');
    await expect(
      dashboard.field(API_KEY_FIELD.label, formOf(dashboard, PROVIDER_KEY_FORM)),
    ).toBeVisible();
  },
);

Then('i dati segreti non sono mostrati in chiaro', async ({ dashboard }) => {
  await expect(
    dashboard.field(API_KEY_FIELD.label, formOf(dashboard, PROVIDER_KEY_FORM)),
  ).toHaveAttribute('type', 'password');
});
