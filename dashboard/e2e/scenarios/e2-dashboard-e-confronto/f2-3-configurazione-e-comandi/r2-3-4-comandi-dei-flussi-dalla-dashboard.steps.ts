import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const STOP_CONFIRMATION = 'Conferma dello stop';
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

Given(
  'che il flusso {string} è fermo e il suo conto non ha capitale libero sufficiente',
  async ({ memory }, flow: string) => {
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

Then(
  'la conferma dice che la posizione su {string} sarà chiusa',
  async ({ dashboard }, asset: string) => {
    await expect(dashboard.confirmation(STOP_CONFIRMATION)).toContainText(
      `La posizione su ${asset} sarà chiusa`,
    );
  },
);

Then(
  'dopo la conferma il flusso {string} è nello stato {string}',
  async ({ dashboard }, flow: string, status: string) => {
    expect(fakePlatform.flowNamed(flow).status).not.toBe(status);
    await dashboard
      .confirmation(STOP_CONFIRMATION)
      .getByRole('button', { name: 'Conferma lo stop' })
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

Then('la dashboard mostra il motivo del rifiuto', async ({ dashboard }) => {
  await expect(dashboard.alert()).toContainText('capitale allocato oltre il capitale libero');
});
