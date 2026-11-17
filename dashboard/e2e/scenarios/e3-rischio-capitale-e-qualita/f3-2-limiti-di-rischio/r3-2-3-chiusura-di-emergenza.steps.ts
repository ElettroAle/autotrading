import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// R3.2.3, ADR chiusura-di-emergenza-nella-dashboard: the confirmation of the dashboard; ADR
// zona-di-emergenza-in-fondo-alla-pagina: the command alone in the zone at the bottom of the page. The other scenarios
// run on the use cases with pytest-bdd.
const EMERGENCY = /Chiusura di emergenza/;

const zoneNamed = (dashboard: DashboardPages, name: string): Locator =>
  dashboard.content().getByRole('region', { name, exact: true });

// Every part of the content that comes after the zone, outside it: none when the zone is at the bottom of the page.
const partsAfter = async (zone: Locator): Promise<string[]> =>
  zone.evaluate((box) => {
    const content = box.closest('main');
    if (content === null) {
      return ['the zone is outside the content of the page'];
    }
    return [...content.querySelectorAll('*')]
      .filter(
        (part) =>
          !box.contains(part) &&
          (part.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_PRECEDING) !== 0 &&
          !part.contains(box),
      )
      .map((part) => part.outerHTML);
  });

const expectAtTheBottom = async (zone: Locator): Promise<void> => {
  await expect(zone).toBeVisible();
  expect(await partsAfter(zone)).toEqual([]);
};
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
    await zoneNamed(dashboard, 'Zona di emergenza')
      .getByRole('button', { name: `Chiusura di emergenza del conto ${accountName}`, exact: true })
      .click();
  },
);

When(
  '{string} apre nella dashboard la pagina del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
    await dashboard.waitUntilRead();
  },
);

When(
  '{string} apre nella dashboard la pagina dei conti',
  async ({ dashboard }, account: string) => {
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    await expect(dashboard.page.getByRole('region', { name: 'Conti' })).toBeVisible();
    await dashboard.waitUntilRead();
  },
);

When(
  '{string} apre nella dashboard le impostazioni generali',
  async ({ dashboard }, account: string) => {
    await dashboard.openAndSignInAs(account);
    await expect(dashboard.flows()).toBeVisible();
    await dashboard.menuEntry('Generale').click();
    await expect(dashboard.page.getByRole('heading', { level: 1 })).toHaveText('Generale');
    await dashboard.waitUntilRead();
  },
);

When(
  '{string} sceglie la chiusura di emergenza del flusso {string} nel riquadro {string}',
  async ({ dashboard, memory }, account: string, flow: string, zone: string) => {
    memory.account = account;
    memory.flow = flow;
    await dashboard.openFlowAs(account, flow);
    await zoneNamed(dashboard, zone)
      .getByRole('button', { name: `Chiusura di emergenza del flusso ${flow}`, exact: true })
      .click();
  },
);

Then(
  'la chiusura di emergenza del flusso {string} sta nel riquadro {string} in fondo alla pagina',
  async ({ dashboard }, flow: string, name: string) => {
    const zone = zoneNamed(dashboard, name);
    await expect(
      zone.getByRole('button', { name: `Chiusura di emergenza del flusso ${flow}`, exact: true }),
    ).toBeVisible();
    await expectAtTheBottom(zone);
  },
);

Then(
  'la chiusura di emergenza di tutti i flussi sta nel riquadro {string} in fondo alla pagina',
  async ({ dashboard }, name: string) => {
    const zone = zoneNamed(dashboard, name);
    await expect(
      zone.getByRole('button', { name: 'Chiusura di emergenza di tutti i flussi', exact: true }),
    ).toBeVisible();
    await expectAtTheBottom(zone);
  },
);

Then(
  'il riquadro {string} in fondo alla pagina contiene la chiusura di emergenza dei conti {string} e {string}',
  async ({ dashboard }, name: string, first: string, second: string) => {
    const zone = zoneNamed(dashboard, name);
    await expect(zone.getByRole('button')).toHaveText([
      `Chiusura di emergenza del conto ${first}`,
      `Chiusura di emergenza del conto ${second}`,
    ]);
    await expectAtTheBottom(zone);
  },
);

Then('il riquadro {string} non contiene altri comandi', async ({ dashboard }, name: string) => {
  const zone = zoneNamed(dashboard, name);
  await expect(zone.getByRole('button')).toHaveCount(1);
  await expect(zone.getByRole('button')).toHaveText(EMERGENCY);
  await expect(zone.getByRole('link')).toHaveCount(0);
});

Then(
  'i comandi del flusso {string} non contengono la chiusura di emergenza',
  async ({ dashboard }, flow: string) => {
    const head = dashboard.content().getByRole('region', { name: flow, exact: true });
    await expect(head.getByRole('group', { name: 'Comandi del flusso' })).toBeVisible();
    await expect(head.getByRole('button', { name: EMERGENCY })).toHaveCount(0);
  },
);

// ADR voce-generale-con-la-zona-pericolosa: the page of every day offers no emergency closing.
Then("l'elenco dei flussi non contiene la chiusura di emergenza", async ({ dashboard }) => {
  await dashboard.menuEntry('Flussi').click();
  await expect(dashboard.flows().getByRole('link').first()).toBeVisible();
  await dashboard.waitUntilRead();
  await expect(dashboard.content().getByRole('button', { name: EMERGENCY })).toHaveCount(0);
  await expect(zoneNamed(dashboard, 'Zona di emergenza')).toHaveCount(0);
});

Then('i comandi dei conti non contengono la chiusura di emergenza', async ({ dashboard }) => {
  const accounts = dashboard.page.getByRole('region', { name: 'Conti' });
  await expect(accounts.getByRole('button').first()).toBeVisible();
  await expect(accounts.getByRole('button', { name: EMERGENCY })).toHaveCount(0);
});
