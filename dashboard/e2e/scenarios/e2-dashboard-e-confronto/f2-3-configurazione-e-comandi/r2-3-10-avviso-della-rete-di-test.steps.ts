import { expect } from '@playwright/test';

import { FAKE_EXCHANGE, fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const TEST_NETWORK_NOTICE = /rete di test/;

// The user acting in a step is the one the background signed in.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

const testNetworkNotice = (subject: string, networkName: string): string =>
  `${subject} opererà sulla rete di test "${networkName}", senza denaro reale`;

// An account of the user on the exchange, once the exchange is configured on the network the scenario names.
const accountOn = async (
  dashboard: DashboardPages,
  account: string,
  name: string,
  network: 'test' | 'real',
  networkName?: string,
): Promise<void> => {
  fakePlatform.configureExchangeNetwork(network, networkName);
  fakePlatform.addAccount(account, name);
  await dashboard.openAccounts();
};

// A flow of the user on an account of the exchange configured on the network the scenario names.
const flowOn = (
  memory: ScenarioMemory,
  flow: string,
  network: 'test' | 'real',
  networkName?: string,
): void => {
  fakePlatform.configureExchangeNetwork(network, networkName);
  fakePlatform.giveFlowTo(memory.account, flow);
};

Given(
  "che l'exchange {string} è configurato sulla rete di test {string}",
  async ({ dashboard }, exchange: string, networkName: string) => {
    expect(exchange).toBe(FAKE_EXCHANGE);
    fakePlatform.configureExchangeNetwork('test', networkName);
    await dashboard.openAccounts();
  },
);

Then(
  'la registrazione avvisa che il conto opererà sulla rete di test {string} senza denaro reale',
  async ({ dashboard }, networkName: string) => {
    const form = dashboard.page.getByRole('region', { name: 'Nuovo conto' });
    await expect(form.getByRole('note')).toHaveText(testNetworkNotice('Il conto', networkName));
  },
);

Given(
  'che {string} ha il conto {string} su un exchange configurato sulla rete di test {string}',
  async ({ dashboard }, account: string, name: string, networkName: string) => {
    await accountOn(dashboard, account, name, 'test', networkName);
  },
);

Given(
  'che {string} ha il conto {string} su un exchange configurato sulla rete reale',
  async ({ dashboard }, account: string, name: string) => {
    await accountOn(dashboard, account, name, 'real');
  },
);

When('{string} apre i suoi conti', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.openAccounts();
});

Then(
  'il conto {string} è segnato come rete di test {string}',
  async ({ dashboard }, name: string, networkName: string) => {
    await expect(dashboard.accountNetwork(name)).toHaveText(`TEST · ${networkName}`, {
      useInnerText: true,
    });
  },
);

Then('il conto {string} è segnato come rete reale', async ({ dashboard }, name: string) => {
  await expect(dashboard.accountNetwork(name)).toHaveText(/^REALE · /, {
    useInnerText: true,
  });
});

Given(
  'che il flusso {string} è assegnato a un conto sulla rete di test {string}',
  ({ memory }, flow: string, networkName: string) => {
    flowOn(memory, flow, 'test', networkName);
  },
);

Given(
  'che il flusso {string} è assegnato a un conto sulla rete reale',
  ({ memory }, flow: string) => {
    flowOn(memory, flow, 'real');
  },
);

Then(
  'la pagina avvisa che il flusso opera sulla rete di test {string} senza denaro reale',
  async ({ dashboard }, networkName: string) => {
    await expect(dashboard.page.getByRole('note')).toHaveText(
      testNetworkNotice('Il flusso', networkName),
    );
  },
);

Then("la pagina non mostra l'avviso della rete di test", async ({ dashboard }) => {
  await expect(dashboard.flowName()).toBeVisible();
  await expect(dashboard.page.getByText(TEST_NETWORK_NOTICE)).toHaveCount(0);
});
