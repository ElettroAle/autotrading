import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import { Given, When } from '../../../support/fixtures';

// R3.2.3, ADR chiusura-di-emergenza-nella-dashboard: the confirmation of the dashboard; the other scenarios run on the
// use cases with pytest-bdd.
const activeFlowWithPosition = (
  account: string,
  accountName: string,
  flow: string,
  asset: string,
): void => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.addUser(account, { hasUserRole: true });
  }
  fakePlatform.addFlow(account, flow, { accountName, assets: [asset] });
  fakePlatform.holdPositions(flow, [anOpenPosition({ asset })]);
};

Given(
  'che {string} ha sul conto {string} i flussi attivi {string} con una posizione su {string} e {string} con una posizione su {string}',
  async (
    { memory },
    account: string,
    accountName: string,
    first: string,
    firstAsset: string,
    second: string,
    secondAsset: string,
  ) => {
    activeFlowWithPosition(account, accountName, first, firstAsset);
    activeFlowWithPosition(account, accountName, second, secondAsset);
    memory.flow = first;
  },
);

Given(
  'che {string} ha sul conto {string} il flusso attivo {string} con una posizione su {string}',
  async ({}, account: string, accountName: string, flow: string, asset: string) => {
    activeFlowWithPosition(account, accountName, flow, asset);
  },
);

When(
  '{string} sceglie nella dashboard la chiusura di emergenza del conto {string}',
  async ({ dashboard, memory }, account: string, accountName: string) => {
    memory.account = account;
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    await dashboard
      .accountRow(accountName)
      .getByRole('button', { name: 'Chiusura di emergenza' })
      .click();
  },
);
