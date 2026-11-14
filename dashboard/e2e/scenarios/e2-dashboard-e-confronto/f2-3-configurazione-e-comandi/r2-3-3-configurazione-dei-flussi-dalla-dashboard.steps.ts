import { expect } from '@playwright/test';

import {
  configurationOf,
  fakePlatform,
  type FakeFlowConfiguration,
} from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const MODEL = 'openrouter/deepseek-chat';
const SAVE = 'Salva le modifiche';

type SourceChoice = { readonly name: string; readonly weight: number };

type NewFlow = {
  readonly name: string;
  readonly account: string;
  readonly assets: string;
  readonly minutes: number;
  readonly sources: readonly SourceChoice[];
  readonly model: string;
  readonly capital: number;
};

// The user acting in a step is the one the background signed in.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

// The risk limits are required: the scenarios that do not name them take ones any configuration admits.
const fillNewFlow = async (dashboard: DashboardPages, flow: NewFlow): Promise<void> => {
  await dashboard.openNewFlow();
  await dashboard.field('Nome').fill(flow.name);
  await dashboard.field('Conto').selectOption({ label: flow.account });
  for (const asset of flow.assets.split(',').map((name) => name.trim())) {
    await dashboard.chooseAsset(asset);
  }
  await dashboard.field('Intervallo del ciclo in minuti').fill(String(flow.minutes));
  for (const source of flow.sources) {
    await dashboard.page.getByRole('checkbox', { name: source.name, exact: true }).check();
    await dashboard.field(`Peso di ${source.name}`).fill(String(source.weight));
  }
  await dashboard.field('Modello').selectOption(flow.model);
  await dashboard.field('Leva massima').fill('3');
  await dashboard.field('Esposizione massima del margine (%)').fill('10');
  await dashboard.field('Capitale allocato').fill(String(flow.capital));
  await dashboard.button('Crea il flusso').click();
};

const flowOnAccount = (
  memory: ScenarioMemory,
  name: string,
  configuration: Partial<FakeFlowConfiguration>,
): void => {
  fakePlatform.addConfiguredFlow(memory.account, name, {
    account_id: fakePlatform.accountNamed('principale').id,
    model: { name: MODEL, parameters: { temperature: '1' } },
    risk_limits: {
      max_leverage: 3,
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: null,
    },
    ...configuration,
  });
};

Given(
  'che {string} ha il conto {string} con capitale libero {int} USDC e una chiave per {string}',
  async (
    { dashboard, memory },
    account: string,
    accountName: string,
    free: number,
    provider: string,
  ) => {
    memory.account = account;
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.giveAccountTo(account, accountName, free);
    fakePlatform.saveProviderKey(account, provider, '2026-11-14T09:00:00+00:00');
    await dashboard.openAndSignInAs(account);
    await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
  },
);

Given(
  'che il flusso {string} è alla versione {int}',
  async ({ memory }, name: string, version: number) => {
    memory.flow = name;
    flowOnAccount(memory, name, {
      version,
      assets: ['BTC'],
      sources: [
        { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 10 } },
        { name: 'sentiment', weight: 1, parameters: {} },
      ],
      allocated_capital: '300',
    });
    expect(configurationOf(fakePlatform.flowNamed(name)).version).toBe(version);
  },
);

Given(
  'che il flusso {string} usa {string} sul conto {string}',
  async ({ memory }, name: string, asset: string, accountName: string) => {
    flowOnAccount(memory, name, {
      account_id: fakePlatform.accountNamed(accountName).id,
      assets: [asset],
      allocated_capital: '100',
    });
    expect(configurationOf(fakePlatform.flowNamed(name)).assets).toEqual([asset]);
  },
);

When(
  '{string} crea il flusso {string} su {string} con asset {string}, intervallo {int} minuti, fonti {string} peso {int} e {string} peso {int}, modello {string} e capitale {int} USDC',
  async (
    { dashboard, memory },
    account: string,
    name: string,
    accountName: string,
    assets: string,
    minutes: number,
    firstSource: string,
    firstWeight: number,
    secondSource: string,
    secondWeight: number,
    model: string,
    capital: number,
  ) => {
    expectSignedIn(memory, account);
    await fillNewFlow(dashboard, {
      name,
      account: accountName,
      assets,
      minutes,
      sources: [
        { name: firstSource, weight: firstWeight },
        { name: secondSource, weight: secondWeight },
      ],
      model,
      capital,
    });
  },
);

When(
  '{string} crea un flusso con capitale {int} USDC su {string}',
  async ({ dashboard, memory }, account: string, capital: number, accountName: string) => {
    expectSignedIn(memory, account);
    await fillNewFlow(dashboard, {
      name: 'nuovo',
      account: accountName,
      assets: 'BTC',
      minutes: 15,
      sources: [],
      model: MODEL,
      capital,
    });
  },
);

When(
  '{string} cambia il peso della fonte {string} a {int}',
  async ({ dashboard, memory }, account: string, source: string, weight: number) => {
    expectSignedIn(memory, account);
    await dashboard.openFlowEditor(memory.flow);
    await dashboard.field(`Peso di ${source}`).fill(String(weight));
    await dashboard.button(SAVE).click();
  },
);

When(
  '{string} aggiunge {string} al flusso {string}',
  async ({ dashboard, memory }, account: string, asset: string, name: string) => {
    expectSignedIn(memory, account);
    if (!fakePlatform.flowsOf(account).some((flow) => flow.name === name)) {
      flowOnAccount(memory, name, { assets: ['BTC'], allocated_capital: '100' });
    }
    await dashboard.openFlowEditor(name);
    await expect(dashboard.chosenAssets()).toHaveText(['BTC×']);
    await dashboard.chooseAsset(asset);
    await dashboard.button(SAVE).click();
  },
);

Then(
  "il flusso {string} compare nell'elenco nello stato {string} alla versione {int}",
  async ({ dashboard }, name: string, status: string, version: number) => {
    const row = dashboard.flowInList(name);
    await expect(row.getByLabel('Stato')).toHaveText(status);
    await expect(row.getByLabel('Versione')).toHaveText(String(version));
  },
);

Then('la dashboard mostra il motivo del rifiuto accanto al capitale', async ({ dashboard }) => {
  await expect(dashboard.field('Capitale allocato')).toHaveAccessibleDescription(
    'capitale allocato oltre il capitale libero: 500 USDC',
  );
});

Then('il flusso non viene creato', async ({ dashboard, memory }) => {
  await expect(dashboard.pageHeading()).toHaveText('Nuovo flusso');
  expect(fakePlatform.flowsOf(memory.account)).toEqual([]);
});

Then(
  'il flusso {string} è alla versione {int} con peso {int} per {string}',
  async ({ dashboard }, name: string, version: number, weight: number, source: string) => {
    await expect(dashboard.message(`Modifiche salvate: versione ${version}`)).toBeVisible();
    await expect(dashboard.field(`Peso di ${source}`)).toHaveValue(String(weight));
    expect(configurationOf(fakePlatform.flowNamed(name)).version).toBe(version);
  },
);

Then(
  'la dashboard mostra che {string} è già usato dal flusso {string}',
  async ({ dashboard }, asset: string, flow: string) => {
    await expect(dashboard.field('Asset')).toHaveAccessibleDescription(
      `asset già assegnati al flusso ${flow} sullo stesso conto: ${asset}`,
    );
  },
);
