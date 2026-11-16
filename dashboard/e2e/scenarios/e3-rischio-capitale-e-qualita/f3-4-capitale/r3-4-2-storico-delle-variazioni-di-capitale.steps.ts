import { expect } from '@playwright/test';

import { aCapitalChange } from '@/testing/mocks/capital-changes';
import { fakePlatform } from '@/testing/mocks/platform';
import { formatInstant } from '@/utils/format-instant';

import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

// R3.4.2, ADR storico-delle-variazioni-di-capitale: the other scenarios run on the use cases with pytest-bdd.
Given(
  'che {string} ha sul conto {string} i flussi {string} con capitale allocato {int} USDC e {string} con capitale allocato {int} USDC',
  async (
    { memory },
    account: string,
    accountName: string,
    first: string,
    firstCapital: number,
    second: string,
    secondCapital: number,
  ) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, first, {
      accountName,
      allocatedCapital: firstCapital,
      currentCapital: firstCapital,
    });
    fakePlatform.addFlow(account, second, {
      accountName,
      assets: ['ETH'],
      allocatedCapital: secondCapital,
      currentCapital: secondCapital,
    });
    memory.flow = first;
  },
);

Given(
  'che {string} ha aumentato di {int} USDC il capitale di {string}',
  async ({ memory }, account: string, amount: number, flowName: string) => {
    const flow = fakePlatform.user(account).flows.find((candidate) => candidate.name === flowName);
    if (flow === undefined) {
      throw new Error(`no flow ${flowName} for ${account}`);
    }
    const previous = flow.allocatedCapital ?? 0;
    const change = aCapitalChange(flow, previous, previous + amount, new Date());
    fakePlatform.recordCapitalChange(change);
    memory.capitalChangedAt = change.changed_at;
    fakePlatform.changeFlow(flowName, { allocatedCapital: previous + amount });
  },
);

When(
  '{string} apre nella dashboard lo storico delle variazioni di {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.page.getByRole('link', { name: 'Capitale', exact: true }).click();
  },
);

Then(
  'la tabella mostra data e ora, motivo {string}, importo {int} USDC, capitale prima {int} USDC e dopo {int} USDC',
  async ({ dashboard, memory }, reason: string, amount: number, previous: number, next: number) => {
    const row = dashboard.page
      .getByRole('table', { name: 'Variazioni di capitale' })
      .locator('tbody tr')
      .first();
    await expect(dashboard.cell(row, 'Data e ora')).toContainText(
      formatInstant(memory.capitalChangedAt),
    );
    await expect(dashboard.cell(row, 'Motivo')).toContainText(reason);
    await expect(dashboard.cell(row, 'Importo')).toContainText(`${amount} USDC`);
    await expect(dashboard.cell(row, 'Capitale prima')).toContainText(`${previous} USDC`);
    await expect(dashboard.cell(row, 'Capitale dopo')).toContainText(`${next} USDC`);
  },
);
