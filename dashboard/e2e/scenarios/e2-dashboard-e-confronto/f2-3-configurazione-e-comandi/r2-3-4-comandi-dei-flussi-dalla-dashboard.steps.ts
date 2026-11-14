import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const STOP_CONFIRMATION = 'Conferma dello stop';
const START_CONFIRMATION = "Conferma dell'avvio";
// The button that confirms each window, by its title.
const CONFIRM_LABELS: Readonly<Record<string, string>> = {
  [STOP_CONFIRMATION]: 'Conferma lo stop',
  [START_CONFIRMATION]: 'Avvia con denaro reale',
};
// Less than the free capital of the account, on an asset no other flow of the account trades.
const AFFORDABLE_CAPITAL = 100;
// More than the balance of every fake account, so no account has free capital enough for it.
const UNAFFORDABLE_CAPITAL = 5000;

// The user acting in a step is the one the background signed in.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

/** The user on the page of the flow, once the API has answered with it. */
const openFlow = async (dashboard: DashboardPages, flow: string): Promise<void> => {
  await dashboard.openFlow(flow);
  await expect(dashboard.flowName()).toHaveText(flow);
};

const runCommand = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  flow: string,
  command: string,
): Promise<void> => {
  expectSignedIn(memory, account);
  memory.flow = flow;
  await dashboard.flowCommand(command).click();
};

Given(
  'che {string} ha il flusso {string} attivo con una posizione aperta su {string}',
  async ({ dashboard, memory }, account: string, flow: string, asset: string) => {
    memory.account = account;
    fakePlatform.giveFlowTo(account, flow);
    fakePlatform.holdPositions(flow, [anOpenPosition({ asset })]);
    await dashboard.openFlow(flow);
    await dashboard.signInAs(account);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

// A stopped flow ready to start, on an exchange configured on the network the scenario names (Bug 277).
const stoppedFlowOn = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  flow: string,
  network: 'test' | 'real',
): Promise<void> => {
  fakePlatform.configureExchangeNetwork(network);
  fakePlatform.giveFlowTo(memory.account, flow);
  fakePlatform.changeFlow(flow, {
    status: 'fermo',
    assets: ['ETH'],
    allocatedCapital: AFFORDABLE_CAPITAL,
  });
  await openFlow(dashboard, flow);
};

Given(
  'che il flusso {string} è assegnato a un conto su un exchange configurato sulla rete reale',
  async ({ dashboard, memory }, flow: string) => {
    memory.subject = START_CONFIRMATION;
    await stoppedFlowOn(dashboard, memory, flow, 'real');
  },
);

Given(
  'che il flusso {string} è assegnato a un conto su un exchange configurato sulla rete di test',
  async ({ dashboard, memory }, flow: string) => {
    await stoppedFlowOn(dashboard, memory, flow, 'test');
  },
);

Given(
  'che il flusso {string} è fermo e il suo conto non ha capitale libero sufficiente',
  async ({ memory }, flow: string) => {
    memory.refusal = 'capitale allocato oltre il capitale libero';
    fakePlatform.giveFlowTo(memory.account, flow);
    // Its capital exceeds the balance of the account less what the other flows of the account hold.
    fakePlatform.changeFlow(flow, {
      status: 'fermo',
      assets: ['ETH'],
      allocatedCapital: UNAFFORDABLE_CAPITAL,
    });
  },
);

When(
  '{string} mette in pausa il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await runCommand(dashboard, memory, account, flow, 'pausa');
  },
);

When(
  '{string} riprende il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await runCommand(dashboard, memory, account, flow, 'riprendi');
  },
);

When(
  '{string} chiede lo stop del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await runCommand(dashboard, memory, account, flow, 'stop');
  },
);

When(
  '{string} apre il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    expectSignedIn(memory, account);
    await openFlow(dashboard, flow);
  },
);

Then('la conferma avvisa che il flusso opererà con denaro reale', async ({ dashboard, memory }) => {
  await expect(dashboard.confirmation(memory.subject)).toContainText(
    'Il flusso opererà con denaro reale',
  );
});

Then(
  'il flusso {string} è nello stato {string} senza conferma',
  async ({ dashboard }, flow: string, status: string) => {
    await expect(dashboard.flowStatus()).toHaveText(`Stato: ${status}`);
    await expect(dashboard.page.getByRole('alertdialog')).toHaveCount(0);
    expect(fakePlatform.flowNamed(flow).status).toBe(status);
  },
);

Then(
  'la conferma dice che la posizione su {string} sarà chiusa',
  async ({ dashboard, memory }, asset: string) => {
    memory.subject = STOP_CONFIRMATION;
    await expect(dashboard.confirmation(STOP_CONFIRMATION)).toContainText(
      `La posizione su ${asset} sarà chiusa`,
    );
  },
);

Then(
  'dopo la conferma il flusso {string} è nello stato {string}',
  async ({ dashboard, memory }, flow: string, status: string) => {
    expect(fakePlatform.flowNamed(flow).status).not.toBe(status);
    await dashboard
      .confirmation(memory.subject)
      .getByRole('button', { name: CONFIRM_LABELS[memory.subject] })
      .click();
    await expect(dashboard.flowStatus()).toHaveText(`Stato: ${status}`);
    expect(fakePlatform.flowNamed(flow).status).toBe(status);
  },
);

Then('vede i comandi {string} e {string}', async ({ dashboard }, first: string, second: string) => {
  await expect(dashboard.flowCommand(first)).toBeVisible();
  await expect(dashboard.flowCommand(second)).toBeVisible();
});

Then('non vede il comando {string}', async ({ dashboard }, command: string) => {
  await expect(dashboard.flowCommand(command)).toHaveCount(0);
});
