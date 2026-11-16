import { expect } from '@playwright/test';

import { fakePlatform, flowIdOf } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

// R3.4.1, ADR incasso-dei-profitti-nella-dashboard: the other scenarios run on the use cases with pytest-bdd.
Given(
  'che {string} ha sul conto {string} il flusso attivo {string} con capitale allocato {int} USDC',
  async ({ memory }, account: string, accountName: string, flow: string, capital: number) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      accountName,
      allocatedCapital: capital,
      currentCapital: capital,
    });
    memory.flow = flow;
  },
);

Given(
  'che {string} ha valore complessivo {int} USDC con una posizione aperta su {string}',
  async ({}, flow: string, value: number, asset: string) => {
    fakePlatform.changeFlow(flow, { currentCapital: value });
    fakePlatform.holdPositions(flow, [anOpenPosition({ asset })]);
  },
);

When(
  "{string} sceglie nella dashboard l'incasso dei profitti di {string}",
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.page.getByRole('button', { name: 'Incassa i profitti' }).click();
  },
);

Then('la dashboard chiede conferma con {string}', async ({ dashboard }, question: string) => {
  const confirmation = dashboard.page.getByRole('alertdialog', { name: "Conferma dell'incasso" });
  await expect(confirmation).toContainText(question);
});

Then(
  'nessuna posizione viene chiusa finché {string} non conferma',
  async ({ dashboard, memory }, account: string) => {
    expect(memory.account).toBe(account);
    await expect(
      dashboard.page.getByRole('alertdialog', { name: "Conferma dell'incasso" }),
    ).toBeVisible();
    expect(fakePlatform.cashOutsOf(memory.flow)).toBe(0);
    expect(fakePlatform.openPositionsOf(flowIdOf(memory.flow))).toHaveLength(1);
  },
);
