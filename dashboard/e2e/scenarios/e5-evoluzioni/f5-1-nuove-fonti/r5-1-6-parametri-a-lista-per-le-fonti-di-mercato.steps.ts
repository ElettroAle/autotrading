import { expect } from '@playwright/test';

import { FAKE_SOURCES, listParameter, type FakeSource } from '@/testing/mocks/catalogs';
import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { fakeSourceCredentials } from '@/testing/mocks/source-credentials';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// ADR parametri-delle-fonti-come-liste-libere: the scenarios of the api and of the worker run in pytest-bdd.

const FLOW = 'liste';
const SAVE = 'Salva le modifiche';
// The source that declares the new list in the first scenario: any source of the catalog, as nothing names it.
const DECLARING_SOURCE = 'notizie';
// A list no source of the platform declares, so the dashboard can know it only from the declaration.
const NEW_LIST = listParameter('finestre_prova', 'finestre prova', [], [3, 30]);

const sourceDeclaring = (label: string): FakeSource => {
  const source = fakeSourceCredentials
    .sources()
    .find((each) => each.parameters.some((parameter) => parameter.label === label));
  expect(source, `una fonte dichiara il parametro ${label}`).toBeDefined();
  return source as FakeSource;
};

const fieldLabelOf = (source: FakeSource, label: string): string =>
  `${label} di ${source.name} · ${source.adapters[0]?.name ?? ''}`;

// The configuration of the source in the editor of a flow of the user: the source active, with its only adapter.
const openSourceOf = async (
  dashboard: DashboardPages,
  account: string,
  source: FakeSource,
): Promise<void> => {
  fakePlatform.giveFlowTo(account, FLOW);
  await dashboard.openFlowEditor(FLOW);
  await dashboard.signInAs(account);
  await expect(dashboard.field('Nome')).toHaveValue(FLOW);
  await dashboard.page.getByRole('checkbox', { name: source.name, exact: true }).check();
  const adapters = dashboard.page.getByRole('list', { name: `Adapter di ${source.name}` });
  await expect(
    adapters.getByRole('checkbox', { name: source.adapters[0]?.name ?? '', exact: true }),
  ).toBeChecked();
};

const savedParametersOf = (source: string) =>
  configurationOf(fakePlatform.flowNamed(FLOW)).sources.find((each) => each.name === source)
    ?.adapters[0]?.parameters;

Given(
  'che una fonte dichiara un parametro a lista con nome, intervallo e numero massimo di valori',
  async ({}) => {
    expect(FAKE_SOURCES.some((source) => source.name === DECLARING_SOURCE)).toBe(true);
    fakeSourceCredentials.declareParameter(DECLARING_SOURCE, NEW_LIST);
  },
);

When(
  '{string} apre la configurazione della fonte nella dashboard',
  async ({ dashboard }, account: string) => {
    await openSourceOf(dashboard, account, sourceDeclaring(NEW_LIST.label));
  },
);

Then('il campo del parametro compare con il suo intervallo', async ({ dashboard }) => {
  const field = dashboard.field(fieldLabelOf(sourceDeclaring(NEW_LIST.label), NEW_LIST.label));
  await expect(field).toBeVisible();
  await expect(field).toHaveAccessibleDescription(
    `ogni valore tra ${NEW_LIST.minimum} e ${NEW_LIST.maximum}, al massimo ${NEW_LIST.maximum_values} valori`,
  );
});

Then('il salvataggio lo controlla con le regole comuni', async ({ dashboard }) => {
  const field = dashboard.field(fieldLabelOf(sourceDeclaring(NEW_LIST.label), NEW_LIST.label));
  const sources = dashboard.page.getByRole('group', { name: 'Fonti' });
  await field.fill(`5, ${NEW_LIST.maximum + 1}`);
  await dashboard.button(SAVE).click();
  await expect(sources).toHaveAccessibleDescription(
    `${NEW_LIST.label}: ogni valore tra ${NEW_LIST.minimum} e ${NEW_LIST.maximum}`,
  );
  await field.fill('3 4 5 6 7 8 9 10 11');
  await dashboard.button(SAVE).click();
  await expect(sources).toHaveAccessibleDescription(
    `${NEW_LIST.label}: al massimo ${NEW_LIST.maximum_values} valori`,
  );
});

When(
  '{string} scrive {} nel campo {string}',
  async ({ dashboard, memory }, account: string, typed: string, label: string) => {
    const source = sourceDeclaring(label);
    memory.sourceCatalog = [source];
    await openSourceOf(dashboard, account, source);
    await dashboard.field(fieldLabelOf(source, label)).fill(typed);
    await dashboard.button(SAVE).click();
  },
);

Then('la fonte è salvata con {word} [{}]', async ({ memory }, key: string, values: string) => {
  const [source] = memory.sourceCatalog;
  const expected = values.split(',').map((value) => Number(value.trim()));
  await expect.poll(() => savedParametersOf(source?.name ?? '')?.[key]).toEqual(expected);
});
