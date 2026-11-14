import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const NOT_ASSIGNED = 'da assegnare';

// Signs in once per scenario: the later steps act on the page the user is already on.
const onFlowPage = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  flow: string,
): Promise<void> => {
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.openFlowAs(account, flow);
  }
  await expect(dashboard.flowName()).toHaveText(flow);
};

Given(
  'che {string} ha il flusso {string} sul conto {string} con asset {string}, fonti {string} peso {int} e modello {string}',
  async (
    {},
    account: string,
    flow: string,
    accountName: string,
    asset: string,
    source: string,
    weight: number,
    model: string,
  ) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      accountName,
      assets: [asset],
      sources: [{ name: source, weight }],
      model,
    });
  },
);

Given('che {string} ha anche il conto {string}', async ({}, account: string, name: string) => {
  fakePlatform.addAccount(account, name);
});

Given('che {string} ha duplicato il flusso {string}', async ({}, account: string, flow: string) => {
  fakePlatform.duplicate(fakePlatform.user(account), fakePlatform.flowNamed(flow).id);
});

When(
  '{string} duplica il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.command('Duplica');
  },
);

Then(
  'esiste il flusso {string} nello stato {string} alla versione {int}',
  async ({ dashboard }, flow: string, status: string, version: number) => {
    await expect(dashboard.flowName()).toHaveText(flow);
    await expect(dashboard.status(status)).toBeVisible();
    await expect(dashboard.detail('Versione')).toHaveText(String(version));
  },
);

Then(
  'ha fonti {string} peso {int} e modello {string}',
  async ({ dashboard }, source: string, weight: number, model: string) => {
    await expect(dashboard.detail('Fonti')).toHaveText(`${source} (peso ${weight})`);
    await expect(dashboard.detail('Modello')).toHaveText(model);
  },
);

Then('non ha conto, capitale allocato né asset', async ({ dashboard }) => {
  await expect(dashboard.detail('Conto')).toHaveText(NOT_ASSIGNED);
  await expect(dashboard.detail('Capitale allocato')).toHaveText(NOT_ASSIGNED);
  await expect(dashboard.detail('Asset')).toHaveText(NOT_ASSIGNED);
});

When('passa un intervallo intero del flusso {string}', async ({ memory }, flow: string) => {
  memory.freeCapital = fakePlatform.freeCapitalOf('anna', 'principale');
  fakePlatform.passMinutes(fakePlatform.flowNamed(flow).cycleMinutes);
});

Then('il flusso {string} non ha cicli', async ({}, flow: string) => {
  expect(fakePlatform.flowNamed(flow).cycles).toBe(0);
});

Then(
  'il capitale libero del conto {string} non cambia',
  async ({ memory }, accountName: string) => {
    expect(fakePlatform.freeCapitalOf('anna', accountName)).toBe(memory.freeCapital);
  },
);

When(
  "{string} assegna al flusso {string} il conto {string}, {int} USDC e l'asset {string}",
  async (
    { dashboard, memory },
    account: string,
    flow: string,
    accountName: string,
    capital: number,
    asset: string,
  ) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.assign(accountName, String(capital), asset);
    await expect(dashboard.detail('Conto')).toHaveText(accountName);
  },
);

When(
  '{string} avvia il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.command('Avvia');
  },
);

When(
  '{string} avvia il flusso {string} senza assegnare conto, capitale e asset',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.command('Avvia');
  },
);

Then(
  'il flusso {string} è nello stato {string}',
  async ({ dashboard }, flow: string, status: string) => {
    await expect(dashboard.status(status)).toBeVisible();
    expect(fakePlatform.flowNamed(flow).status).toBe(status);
  },
);

Then("l'avvio è rifiutato con il motivo {string}", async ({ dashboard }, reason: string) => {
  await expect(dashboard.alert()).toHaveText(`Avvio rifiutato: ${reason}`);
});

Then(
  "l'avvio è rifiutato perché {string} è già usato dal flusso {string} sul conto {string}",
  async ({ dashboard }, asset: string, holder: string, accountName: string) => {
    await expect(dashboard.alert()).toHaveText(
      `Avvio rifiutato: asset già assegnati al flusso ${holder} sullo stesso conto: ${asset}`,
    );
    expect(fakePlatform.flowNamed(holder).accountId).toBe(
      fakePlatform.accountNamed(accountName).id,
    );
  },
);

Then(
  'il flusso {string} resta nello stato {string}',
  async ({ dashboard }, flow: string, status: string) => {
    await expect(dashboard.status(status)).toBeVisible();
    expect(fakePlatform.flowNamed(flow).status).toBe(status);
  },
);

When(
  '{string} chiede di duplicare il flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    memory.account = account;
    await dashboard.openFlowAs(account, flow);
    const flowId = encodeURIComponent(fakePlatform.flowNamed(flow).id);
    memory.answerStatus = await dashboard.send(account, 'POST', `/flows/${flowId}/duplicate`);
  },
);

Then('la richiesta è rifiutata come flusso inesistente', async ({ dashboard, memory }) => {
  await expect(dashboard.page.getByText('Flusso non trovato.')).toBeVisible();
  await expect(dashboard.page.getByRole('button', { name: 'Duplica' })).toHaveCount(0);
  expect(memory.answerStatus).toBe(404);
  expect(fakePlatform.user(memory.account).flows).toHaveLength(0);
});
