import { expect, type Locator } from '@playwright/test';

import { defaultTextOf } from '@/lib/parameter-lists';
import { FAKE_SOURCES, type FakeSource } from '@/testing/mocks/catalogs';
import { fakePlatform } from '@/testing/mocks/platform';
import { fakeSourceTrials, type FakeSourceTrial } from '@/testing/mocks/source-trials';
import { formatInstant } from '@/utils/format-instant';

import { backdropColourOf, isTransparent, paintedColourOf } from '../../../support/colours';
import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// "La prova non tocca i flussi" has no step here: pytest-bdd runs it on the use cases of the worker (ADR 0116).

const catalogSource = (name: string): FakeSource => {
  const source = FAKE_SOURCES.find((each) => each.name === name);
  expect(source, `la fonte ${name} è nel catalogo`).toBeDefined();
  return source as FakeSource;
};

const card = (dashboard: DashboardPages, source: string): Locator =>
  dashboard.page.getByRole('article', { name: source, exact: true });

const trialForm = (dashboard: DashboardPages, source: string): Locator =>
  card(dashboard, source).getByRole('form', { name: `Prova di ${source}` });

const outcomeOf = (dashboard: DashboardPages, source: string): Locator =>
  card(dashboard, source).getByRole('region', { name: `Esito della prova di ${source}` });

// The source the last trial was about: the steps of the outcome name no source.
const triedSource = (): string => {
  const last = fakeSourceTrials.requests().at(-1);
  expect(last, 'una prova ha raggiunto il worker').toBeDefined();
  return last?.source ?? '';
};

const tryIt = async (dashboard: DashboardPages, source: string): Promise<FakeSourceTrial> => {
  const answer = dashboard.page.waitForResponse((response) => {
    const path = new URL(response.url()).pathname;
    return (
      response.request().method() === 'POST' &&
      path.includes(`/sources/${encodeURIComponent(source)}/adapters/`) &&
      path.endsWith('/trials')
    );
  });
  await trialForm(dashboard, source).getByRole('button', { name: 'Prova' }).click();
  return (await (await answer).json()) as FakeSourceTrial;
};

Given(
  'che {string} è nella pagina Fonti della dashboard',
  async ({ dashboard }, account: string) => {
    fakePlatform.ensureUser(account);
    await dashboard.open('/fonti');
    await dashboard.signInAs(account);
    await expect(dashboard.page.getByRole('heading', { level: 1, name: 'Fonti' })).toBeVisible();
    await expect(card(dashboard, FAKE_SOURCES[0]?.name ?? '')).toBeVisible();
  },
);

Given('che la fonte {string} non risponde', async ({}, source: string) => {
  catalogSource(source);
  fakeSourceTrials.silence(source);
});

When(
  "{string} prova la fonte {string} per l'asset {string} con i parametri predefiniti",
  async ({ dashboard, memory }, _account: string, source: string, asset: string) => {
    const form = trialForm(dashboard, source);
    await form.getByLabel('Asset').selectOption(asset);
    for (const parameter of catalogSource(source).adapters[0]?.parameters ?? []) {
      await expect(form.getByLabel(parameter.label)).toHaveValue(defaultTextOf(parameter));
    }
    memory.sourceTrial = await tryIt(dashboard, source);
  },
);

When(
  '{string} prova la fonte {string}',
  async ({ dashboard, memory }, _account: string, source: string) => {
    if (catalogSource(source).per_asset) {
      await expect(trialForm(dashboard, source).getByLabel('Asset')).not.toHaveValue('');
    }
    memory.sourceTrial = await tryIt(dashboard, source);
  },
);

When(
  '{string} prova la fonte {string} con un periodo fuori dai limiti',
  async ({ dashboard, memory }, _account: string, source: string) => {
    const [parameter] = catalogSource(source).adapters[0]?.parameters ?? [];
    expect(parameter, `la fonte ${source} ha un parametro con limiti`).toBeDefined();
    memory.sourceParameter = parameter;
    const form = trialForm(dashboard, source);
    await form.getByLabel(parameter?.label ?? '').fill(String((parameter?.maximum ?? 0) + 1));
    await form.getByRole('button', { name: 'Prova' }).click();
  },
);

Then(
  "vede l'esito {string}, i valori letti, l'istante dei dati e il tempo di risposta",
  async ({ dashboard, memory }, outcome: string) => {
    const trial = memory.sourceTrial;
    expect(trial?.outcome, 'la prova è riuscita').toBe('succeeded');
    const shown = outcomeOf(dashboard, triedSource());
    await expect(shown).toContainText(outcome);
    for (const value of trial?.values ?? []) {
      for (const [key, read] of Object.entries(value.values)) {
        await expect(shown).toContainText(`${key}${read}`);
      }
    }
    expect(trial?.values.length).toBeGreaterThan(0);
    await expect(shown).toContainText(formatInstant(trial?.data_at ?? ''));
    await expect(shown).toContainText(`${String(trial?.response_milliseconds)} ms`);
  },
);

Then(
  "vede l'esito {string} con il motivo e l'indicazione {string}",
  async ({ dashboard, memory }, outcome: string, kind: string) => {
    const trial = memory.sourceTrial;
    expect(trial?.outcome, 'la prova è fallita').toBe('failed');
    const shown = outcomeOf(dashboard, triedSource());
    await expect(shown).toContainText(outcome);
    await expect(shown).toContainText(trial?.reason ?? 'un motivo');
    await expect(shown).toContainText(kind);
  },
);

Then(
  'la prova non parte e il parametro mostra il limite ammesso',
  async ({ dashboard, memory }) => {
    const parameter = memory.sourceParameter;
    const field = dashboard.page.getByLabel(parameter?.label ?? '', { exact: true });
    await expect(field).toHaveAttribute('aria-invalid', 'true');
    await expect(field).toHaveAccessibleDescription(
      `ammesso da ${String(parameter?.minimum)} a ${String(parameter?.maximum)}`,
    );
    expect(fakeSourceTrials.requests()).toEqual([]);
  },
);

// Bug 726: the card of a source is filled with a colour of its own, not the background of the page seen through it.
Then(
  'ogni fonte sta in un riquadro con uno sfondo diverso da quello della pagina',
  async ({ dashboard }) => {
    const cards = await dashboard.page.getByRole('article').all();
    expect(cards.length, 'la pagina mostra le fonti').toBeGreaterThan(0);
    for (const sourceCard of cards) {
      const background = await paintedColourOf(sourceCard, 'backgroundColor');
      expect(isTransparent(background), 'il riquadro ha uno sfondo proprio').toBe(false);
      expect(background, 'lo sfondo del riquadro non è quello della pagina').not.toEqual(
        await backdropColourOf(sourceCard),
      );
    }
  },
);
