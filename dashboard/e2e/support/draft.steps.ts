import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Then, When } from './fixtures';
import { onFlowPage } from './flow-page';

// Shared by the requirements that make a draft, from a copy or from a file (R2.4.1, R2.5.2; ADR 0124): what the
// draft lacks, its assignment and its start.

const NOT_ASSIGNED = 'da assegnare';

Then('non ha conto, capitale allocato né asset', async ({ dashboard }) => {
  await expect(dashboard.detail('Conto')).toHaveText(NOT_ASSIGNED);
  await expect(dashboard.detail('Capitale allocato')).toHaveText(NOT_ASSIGNED);
  await expect(dashboard.detail('Asset')).toHaveText(NOT_ASSIGNED);
});

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
