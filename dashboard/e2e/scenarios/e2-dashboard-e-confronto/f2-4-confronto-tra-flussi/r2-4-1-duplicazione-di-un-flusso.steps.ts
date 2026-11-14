import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

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
