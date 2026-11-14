import { expect, type Locator } from '@playwright/test';

import { FAKE_MODELS } from '@/testing/mocks/catalogs';
import { FAKE_SUPPORTED_EXCHANGES, fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const ACCOUNT_FORM = 'Nuovo conto';
const PROVIDER_KEY_FORM = 'Nuova chiave';
const OUTSIDE_THE_LIST = 'exchange-fuori-elenco';

const formOf = (dashboard: DashboardPages, name: string): Locator =>
  dashboard.page.getByRole('region', { name });

const optionOf = (field: Locator, value: string): Locator =>
  field.locator(`option[value="${value}"]`);

// The user signs in on the page of the form: the sign-in brings the user back to the page asked for.
const openFormAs = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  open: () => Promise<void>,
  form: string,
): Promise<void> => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.addUser(account, { hasUserRole: true });
  }
  memory.account = account;
  await open();
  await dashboard.signInAs(account);
  await expect(formOf(dashboard, form)).toBeVisible();
};

Given("che la piattaforma supporta l'exchange {string}", async ({}, exchange: string) => {
  expect(FAKE_SUPPORTED_EXCHANGES).toContain(exchange);
});

Given(
  'che il catalogo dei modelli ha i fornitori {string} e {string}',
  async ({}, first: string, second: string) => {
    const providers = FAKE_MODELS.map((model) => model.provider);
    expect(providers).toEqual(expect.arrayContaining([first, second]));
  },
);

Given("che l'API non riesce a fornire l'elenco degli exchange", async () => {
  fakePlatform.stopListingExchanges();
  expect(fakePlatform.listsExchanges()).toBe(false);
});

When(
  '{string} apre la registrazione di un conto',
  async ({ dashboard, memory }, account: string) => {
    await openFormAs(dashboard, memory, account, () => dashboard.openAccounts(), ACCOUNT_FORM);
  },
);

When(
  '{string} apre la registrazione di una chiave IA',
  async ({ dashboard, memory }, account: string) => {
    await openFormAs(
      dashboard,
      memory,
      account,
      () => dashboard.openProviderKeys(),
      PROVIDER_KEY_FORM,
    );
  },
);

Then(
  "il campo exchange offre {string} e non accetta un valore fuori dall'elenco",
  async ({ dashboard }, exchange: string) => {
    const field = dashboard.field('Exchange', formOf(dashboard, ACCOUNT_FORM));
    await expect(optionOf(field, exchange)).toBeEnabled();
    const kept = await field.evaluate((select: HTMLSelectElement, outside: string) => {
      select.value = outside;
      return select.value;
    }, OUTSIDE_THE_LIST);
    expect(kept).toBe('');
  },
);

Then(
  'il campo fornitore offre {string} e {string}',
  async ({ dashboard }, first: string, second: string) => {
    const field = dashboard.field('Fornitore', formOf(dashboard, PROVIDER_KEY_FORM));
    await expect(optionOf(field, first)).toBeEnabled();
    await expect(optionOf(field, second)).toBeEnabled();
  },
);

Then(
  'il fornitore {string} risulta già registrato e non si può scegliere',
  async ({ dashboard }, provider: string) => {
    const option = optionOf(
      dashboard.field('Fornitore', formOf(dashboard, PROVIDER_KEY_FORM)),
      provider,
    );
    await expect(option).toHaveText(`${provider} · chiave già registrata`);
    await expect(option).toBeDisabled();
  },
);

Then(
  "il modulo segnala che l'elenco non è disponibile e non permette la registrazione",
  async ({ dashboard }) => {
    const form = formOf(dashboard, ACCOUNT_FORM);
    await expect(form.getByRole('alert')).toHaveText(
      'Impossibile leggere gli exchange supportati: errore interno',
    );
    await expect(dashboard.field('Exchange', form)).toBeDisabled();
    await expect(form.getByRole('button', { name: 'Registra il conto' })).toBeDisabled();
  },
);
