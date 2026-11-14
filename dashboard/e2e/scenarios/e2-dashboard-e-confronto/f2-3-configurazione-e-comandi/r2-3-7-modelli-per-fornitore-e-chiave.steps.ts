import { expect, type Locator } from '@playwright/test';

import { FAKE_MODELS } from '@/testing/mocks/catalogs';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const ACCOUNT_NAME = 'principale';
const PROVIDER_KEYS_LINK = 'Chiavi dei fornitori IA';

// The user signs in once, on the form of a new flow: the sign-in brings the user back to the page asked for.
const openNewFlowAs = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
): Promise<void> => {
  await dashboard.openNewFlow();
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.signInAs(account);
  }
  await expect(dashboard.field('Modello')).toBeVisible();
};

/** The models of a group of the drop-down of the model, the group named by its provider and the state of its key. */
const groupOf = (dashboard: DashboardPages, provider: string, keyState: string): Locator =>
  dashboard.field('Modello').locator(`optgroup[label="${provider} · chiave ${keyState}"]`);

const modelOption = (scope: Locator, model: string): Locator =>
  scope.getByRole('option', { name: model, exact: true });

Given(
  'che il catalogo contiene i modelli {string} e {string}',
  async ({}, first: string, second: string) => {
    expect(FAKE_MODELS.map((model) => model.name)).toEqual(expect.arrayContaining([first, second]));
  },
);

Given(
  'che {string} ha il flusso {string} con modello {string}',
  async ({}, account: string, name: string, model: string) => {
    fakePlatform.addConfiguredFlow(account, name, {
      account_id: fakePlatform.accountNamed(ACCOUNT_NAME).id,
      model: { name: model, parameters: {} },
    });
    expect(fakePlatform.flowNamed(name).model).toBe(model);
  },
);

When(
  '{string} apre il modulo di creazione di un flusso',
  async ({ dashboard, memory }, account: string) => {
    await openNewFlowAs(dashboard, memory, account);
  },
);

When(
  '{string} sceglie il modello {string} nel modulo di creazione di un flusso',
  async ({ dashboard, memory }, account: string, model: string) => {
    await openNewFlowAs(dashboard, memory, account);
    await dashboard.field('Modello').selectOption(model);
  },
);

When(
  '{string} apre la modifica del flusso {string}',
  async ({ dashboard, memory }, account: string, name: string) => {
    memory.account = account;
    await dashboard.openFlowEditor(name);
    await dashboard.signInAs(account);
    await expect(dashboard.field('Modello')).toBeVisible();
  },
);

Then(
  'la tendina del modello ha il gruppo {string} con chiave registrata che contiene {string}',
  async ({ dashboard }, provider: string, model: string) => {
    await expect(modelOption(groupOf(dashboard, provider, 'registrata'), model)).toBeAttached();
  },
);

Then(
  'ha il gruppo {string} con chiave mancante che contiene {string}',
  async ({ dashboard }, provider: string, model: string) => {
    await expect(modelOption(groupOf(dashboard, provider, 'mancante'), model)).toBeAttached();
  },
);

Then('il modello {string} non si può scegliere', async ({ dashboard }, model: string) => {
  await expect(modelOption(dashboard.field('Modello'), model)).toBeDisabled();
});

Then('il modulo offre il collegamento alle chiavi IA', async ({ dashboard }) => {
  await expect(
    dashboard.page
      .getByRole('form', { name: 'Configurazione del flusso' })
      .getByRole('link', { name: PROVIDER_KEYS_LINK }),
  ).toHaveAttribute('href', '/dashboard/provider-keys');
});

Then('il modulo mostra i parametri del modello {string}', async ({ dashboard }, model: string) => {
  const parameters = FAKE_MODELS.find((candidate) => candidate.name === model)?.parameters ?? [];
  expect(parameters).not.toEqual([]);
  const group = dashboard.page.getByRole('group', { name: 'Parametri del modello' });
  for (const parameter of parameters) {
    await expect(group.getByLabel(parameter.label, { exact: true })).toBeVisible();
  }
});

Then(
  'il modello {string} resta indicato come scelta attuale con chiave mancante',
  async ({ dashboard }, model: string) => {
    const provider = model.split('/')[0] ?? '';
    await expect(dashboard.field('Modello')).toHaveValue(model);
    await expect(modelOption(groupOf(dashboard, provider, 'mancante'), model)).toBeEnabled();
  },
);
