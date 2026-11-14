import { expect } from '@playwright/test';

import { fakePlatform, type FakeStrategyDocument } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';
import { onFlowPage, onFlowsPage } from '../../../support/flow-page';

// The parts of a flow the file never carries (RF-21.06): where the strategy runs, with how much, with which keys.
const EXCLUDED_KEYS = [
  'account',
  'account_id',
  'allocated_capital',
  'capital',
  'assets',
  'key',
  'keys',
];
const IMPORTED_NAME = 'importato';
const RETIRED_MODEL = 'openrouter/modello-ritirato';

const exportedFrom = (account: string, flow: string): FakeStrategyDocument =>
  fakePlatform.exportStrategy(fakePlatform.user(account), fakePlatform.flowNamed(flow).id).document;

const keysOf = (document: unknown): string[] => {
  if (Array.isArray(document)) {
    return document.flatMap(keysOf);
  }
  if (typeof document === 'object' && document !== null) {
    return Object.entries(document).flatMap(([key, value]) => [key, ...keysOf(value)]);
  }
  return [];
};

const strategyOf = (memory: ScenarioMemory): FakeStrategyDocument['strategy'] =>
  (JSON.parse(memory.strategyFile) as FakeStrategyDocument).strategy;

const flowNamesOf = (account: string): string[] =>
  fakePlatform.user(account).flows.map((flow) => flow.name);

/** A file exported from the flow of the background, with its model replaced, or removed when none is given. */
const fileWithModel = (account: string, flow: string, model?: string): string => {
  const { strategy, ...document } = exportedFrom(account, flow);
  const withoutModel = Object.fromEntries(
    Object.entries(strategy).filter(([part]) => part !== 'model'),
  );
  const changed =
    model === undefined
      ? withoutModel
      : { ...withoutModel, model: { name: model, parameters: {} } };
  return JSON.stringify({ ...document, strategy: changed });
};

const importFile = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  { name, file }: { name: string; file: string },
): Promise<void> => {
  await onFlowsPage(dashboard, memory, account);
  memory.flowsBefore = flowNamesOf(account);
  await dashboard.importStrategy(name, file);
};

Given(
  'che {string} ha il flusso {string} con asset {string}, fonti {string} peso {int}, modello {string} e capitale {int} USDC sul conto {string}',
  async (
    { memory },
    account: string,
    flow: string,
    asset: string,
    source: string,
    weight: number,
    model: string,
    capital: number,
    accountName: string,
  ) => {
    memory.flow = flow;
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      accountName,
      assets: [asset],
      sources: [{ name: source, weight }],
      model,
      allocatedCapital: capital,
    });
  },
);

When(
  '{string} esporta il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    const file = await dashboard.exportStrategy();
    expect(file.name).toBe(`${flow}.json`);
    memory.strategyFile = file.content;
  },
);

Then(
  'ottiene un file con fonti {string} peso {int} e modello {string}',
  async ({ memory }, source: string, weight: number, model: string) => {
    const strategy = strategyOf(memory);
    expect(strategy.sources?.map((each) => [each.name, each.weight])).toEqual([[source, weight]]);
    expect(strategy.model?.name).toBe(model);
  },
);

Then('il file non contiene conto, capitale, asset né chiavi', async ({ memory }) => {
  const keys = keysOf(JSON.parse(memory.strategyFile));
  expect(keys.filter((key) => EXCLUDED_KEYS.includes(key))).toEqual([]);
  expect(memory.strategyFile).not.toContain(fakePlatform.accountNamed('principale').id);
  expect(Object.keys(strategyOf(memory)).sort()).toEqual([
    'bring_to_minimum',
    'cycle_minutes',
    'instructions',
    'model',
    'risk_limits',
    'sources',
  ]);
});

Given(
  'che {string} ha esportato il flusso {string}',
  async ({ memory }, account: string, flow: string) => {
    memory.strategyFile = JSON.stringify(exportedFrom(account, flow));
  },
);

When(
  '{string} importa il file con il nome {string}',
  async ({ dashboard, memory }, account: string, name: string) => {
    await importFile(dashboard, memory, account, { name, file: memory.strategyFile });
  },
);

Then(
  'esiste il flusso {string} nello stato {string} alla versione {int} con la strategia di {string}',
  async ({ dashboard }, flow: string, status: string, version: number, original: string) => {
    const source = fakePlatform.flowNamed(original);
    await expect(dashboard.flowName()).toHaveText(flow);
    await expect(dashboard.status(status)).toBeVisible();
    await expect(dashboard.detail('Versione')).toHaveText(String(version));
    await expect(dashboard.detail('Modello')).toHaveText(source.model);
    await expect(dashboard.detail('Fonti')).toHaveText(
      source.sources.map((each) => `${each.name} (peso ${each.weight})`).join(', '),
    );
  },
);

Given(
  'che {string} ha importato il flusso {string}',
  async ({ memory }, account: string, name: string) => {
    fakePlatform.importStrategy(
      fakePlatform.user(account),
      name,
      exportedFrom(account, memory.flow),
    );
  },
);

When('{string} importa un file senza modello', async ({ dashboard, memory }, account: string) => {
  const file = fileWithModel(account, memory.flow);
  await importFile(dashboard, memory, account, { name: IMPORTED_NAME, file });
});

When(
  '{string} importa un file con un modello che non è nel catalogo',
  async ({ dashboard, memory }, account: string) => {
    const file = fileWithModel(account, memory.flow, RETIRED_MODEL);
    await importFile(dashboard, memory, account, { name: IMPORTED_NAME, file });
  },
);

Then("l'importazione è rifiutata con il motivo {string}", async ({ dashboard }, reason: string) => {
  // The reason comes first; what it refers to, the model of the file, may follow it.
  await expect(dashboard.importForm().getByRole('alert')).toHaveText(
    new RegExp(`^Importazione rifiutata: ${reason}(: .+)?$`),
  );
});

Then('nessun flusso viene creato', async ({ dashboard, memory }) => {
  await expect(dashboard.importForm()).toBeVisible();
  expect(flowNamesOf(memory.account)).toEqual(memory.flowsBefore);
  await expect(dashboard.flows().getByRole('listitem')).toHaveCount(memory.flowsBefore.length);
});
