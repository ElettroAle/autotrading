import { expect } from '@playwright/test';

import { FAKE_SOURCES, type FakeSource } from '@/testing/mocks/catalogs';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Then, When } from '../../../support/fixtures';

const SAVE = 'Salva le modifiche';
const NO_CONFIGURATION = 'nessuna configurazione necessaria';

const catalogSource = (name: string): FakeSource => {
  const source = FAKE_SOURCES.find((each) => each.name === name);
  expect(source, `la fonte ${name} è nel catalogo`).toBeDefined();
  return source as FakeSource;
};

const sourceOfAdapter = (adapter: string): FakeSource => {
  const source = FAKE_SOURCES.find((each) =>
    each.adapters.some((offered) => offered.name === adapter),
  );
  expect(source, `una fonte offre l'adapter ${adapter}`).toBeDefined();
  return source as FakeSource;
};

// The steps that name no flow act on the one the background gave the user.
const onlyFlowOf = (account: string): string => {
  const [flow] = fakePlatform.flowsOf(account);
  expect(flow, `${account} ha un flusso`).toBeDefined();
  return flow?.name ?? '';
};

const adaptersOf = (dashboard: DashboardPages, source: string) =>
  dashboard.page.getByRole('list', { name: `Adapter di ${source}` });

// The editor of the flow is where the user meets the sources: the sign-in brings the user back to it.
const openEditorAs = async (
  dashboard: DashboardPages,
  account: string,
  flow: string,
): Promise<void> => {
  await dashboard.openFlowEditor(flow);
  await dashboard.signInAs(account);
  await expect(dashboard.field('Nome')).toHaveValue(flow);
};

const activate = async (dashboard: DashboardPages, source: string): Promise<void> => {
  await dashboard.page.getByRole('checkbox', { name: source, exact: true }).check();
};

When("{string} chiede l'elenco delle fonti", async ({ dashboard, memory }, account: string) => {
  const catalog = dashboard.page.waitForResponse((response) =>
    new URL(response.url()).pathname.endsWith('/sources'),
  );
  await openEditorAs(dashboard, account, onlyFlowOf(account));
  memory.sourceCatalog = (await (await catalog).json()) as FakeSource[];
  for (const source of memory.sourceCatalog) {
    await activate(dashboard, source.name);
  }
});

Then(
  'la fonte {string} ha gli adapter {string} e {string}',
  async ({ dashboard }, source: string, first: string, second: string) => {
    await expect(adaptersOf(dashboard, source).getByRole('checkbox')).toHaveCount(2);
    await expect(
      adaptersOf(dashboard, source).getByRole('checkbox', { name: first, exact: true }),
    ).toBeVisible();
    await expect(
      adaptersOf(dashboard, source).getByRole('checkbox', { name: second, exact: true }),
    ).toBeVisible();
  },
);

Then(
  'ogni adapter dichiara parametri, configurazione richiesta e disponibilità dello storico',
  async ({ dashboard, memory }) => {
    expect(memory.sourceCatalog.length).toBeGreaterThan(0);
    for (const source of memory.sourceCatalog) {
      expect(source.adapters.length).toBeGreaterThan(0);
      for (const adapter of source.adapters) {
        expect(Array.isArray(adapter.parameters)).toBe(true);
        expect(Array.isArray(adapter.configuration_fields)).toBe(true);
        expect(typeof adapter.offers_history).toBe('boolean');
        const configuration =
          adapter.configuration_fields.length === 0
            ? NO_CONFIGURATION
            : adapter.configuration_fields.map((field) => field.label).join(', ');
        await expect(
          adaptersOf(dashboard, source.name).getByRole('checkbox', {
            name: adapter.name,
            exact: true,
          }),
        ).toHaveAccessibleDescription(`${adapter.description} ${configuration}`);
      }
    }
  },
);

Then(
  "l'adapter {string} dichiara {string}",
  async ({ dashboard }, adapter: string, declared: string) => {
    const source = sourceOfAdapter(adapter);
    await expect(
      adaptersOf(dashboard, source.name).getByRole('checkbox', { name: adapter, exact: true }),
    ).toHaveAccessibleDescription(new RegExp(`${declared}$`));
  },
);

When(
  '{string} attiva nel flusso {string} la fonte {string} senza scegliere un adapter',
  async ({ dashboard }, account: string, flow: string, source: string) => {
    expect(catalogSource(source).adapters.length).toBeGreaterThan(1);
    await openEditorAs(dashboard, account, flow);
    await activate(dashboard, source);
    await dashboard.button(SAVE).click();
  },
);

Then(
  'la configurazione è rifiutata con il motivo {string}',
  async ({ dashboard }, reason: string) => {
    await expect(dashboard.page.getByRole('group', { name: 'Fonti' })).toHaveAccessibleDescription(
      reason,
    );
  },
);

When(
  "{string} imposta un parametro dell'adapter {string} a un valore non ammesso",
  async ({ dashboard, memory }, account: string, adapter: string) => {
    const source = sourceOfAdapter(adapter);
    const [parameter] =
      source.adapters.find((offered) => offered.name === adapter)?.parameters ?? [];
    expect(parameter, `l'adapter ${adapter} dichiara un parametro`).toBeDefined();
    memory.sourceParameter = parameter;
    await openEditorAs(dashboard, account, onlyFlowOf(account));
    await activate(dashboard, source.name);
    const choice = adaptersOf(dashboard, source.name).getByRole('checkbox', {
      name: adapter,
      exact: true,
    });
    await choice.check();
    await dashboard.field(`Peso di ${source.name} · ${adapter}`).fill('5');
    await dashboard
      .field(`${parameter?.label} di ${source.name} · ${adapter}`)
      .fill(String((parameter?.maximum ?? 0) + 1));
    await dashboard.button(SAVE).click();
  },
);

Then(
  'la configurazione è rifiutata con il motivo che nomina il parametro e i valori ammessi',
  async ({ dashboard, memory }) => {
    const parameter = memory.sourceParameter;
    expect(parameter).toBeDefined();
    const sources = dashboard.page.getByRole('group', { name: 'Fonti' });
    await expect(sources).toHaveAccessibleDescription(new RegExp(parameter?.label ?? ''));
    await expect(sources).toHaveAccessibleDescription(
      new RegExp(`${parameter?.minimum}\\D+${parameter?.maximum}`),
    );
  },
);

When(
  "{string} sceglie nel flusso {string} l'adapter {string} della fonte {string}",
  async ({ dashboard, memory }, account: string, flow: string, adapter: string, source: string) => {
    await openEditorAs(dashboard, account, flow);
    await activate(dashboard, source);
    await adaptersOf(dashboard, source)
      .getByRole('checkbox', { name: adapter, exact: true })
      .check();
    // The catalog of the scenario keeps the adapter chosen alone, as the form shows it.
    const offered = catalogSource(source);
    memory.sourceCatalog = [
      { ...offered, adapters: offered.adapters.filter((each) => each.name === adapter) },
    ];
  },
);

Then(
  "il modulo dell'adapter ha il peso e un campo per ogni parametro dichiarato, con i limiti e il valore predefinito",
  async ({ dashboard, memory }) => {
    const [source] = memory.sourceCatalog;
    const [declared] = source?.adapters ?? [];
    expect(declared, "l'adapter è nel catalogo").toBeDefined();
    const label = `${source?.name ?? ''} · ${declared?.name ?? ''}`;
    await expect(dashboard.field(`Peso di ${label}`)).toBeVisible();
    expect(declared?.parameters.length).toBeGreaterThan(0);
    for (const parameter of declared?.parameters ?? []) {
      const field = dashboard.field(`${parameter.label} di ${label}`);
      await expect(field).toHaveAttribute('min', String(parameter.minimum));
      await expect(field).toHaveAttribute('max', String(parameter.maximum));
      await expect(field).toHaveAttribute('placeholder', String(parameter.default));
    }
  },
);
