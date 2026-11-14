import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Then, When } from '../../../support/fixtures';

// The areas the page of the flows no longer leads to: the menu does (R2.1.3).
const OTHER_AREAS = ['accounts', 'history', 'provider-keys', 'notifications'];

// The scenarios have no background: the user they name is a user with the Utente role.
When('{string} apre la dashboard', async ({ dashboard }, account: string) => {
  fakePlatform.ensureUser(account);
  await dashboard.openAndSignInAs(account);
});

When(
  '{string} apre il dettaglio del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    fakePlatform.giveFlowTo(account, flow);
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

When(
  '{string} sceglie {string} nella pagina dei flussi',
  async ({ dashboard }, account: string, command: string) => {
    fakePlatform.ensureUser(account);
    await dashboard.openAndSignInAs(account);
    // The import is on request: closed until the user asks for it.
    await expect(dashboard.flowViews()).toBeVisible();
    await expect(dashboard.importForm()).toHaveCount(0);
    await dashboard.content().getByRole('button', { name: command, exact: true }).click();
  },
);

When('{string} apre la voce {string}', async ({ dashboard }, account: string, entry: string) => {
  fakePlatform.ensureUser(account);
  await dashboard.openAndSignInAs(account);
  await dashboard.menuEntry(entry).click();
});

Then(
  'il menu ha le voci {string}, {string}, {string}',
  async ({ dashboard }, first: string, second: string, third: string) => {
    for (const entry of [first, second, third]) {
      await expect(dashboard.menuEntry(entry)).toBeVisible();
    }
  },
);

Then(
  'ha il gruppo {string} con le voci {string} e {string}',
  async ({ dashboard }, group: string, first: string, second: string) => {
    await expect(dashboard.menu().getByText(group, { exact: true })).toBeVisible();
    await expect(
      dashboard.menuGroup(group).getByRole('link', { name: first, exact: true }),
    ).toBeVisible();
    await expect(
      dashboard.menuGroup(group).getByRole('link', { name: second, exact: true }),
    ).toBeVisible();
  },
);

Then('la voce {string} del menu è evidenziata', async ({ dashboard }, entry: string) => {
  await expect(dashboard.menuEntry(entry)).toHaveAttribute('aria-current', 'page');
  await expect(dashboard.menu().locator('[aria-current="page"]')).toHaveCount(1);
});

Then(
  'la pagina offre {string}, {string} e la vista {string}',
  async ({ dashboard }, newFlow: string, importCommand: string, view: string) => {
    await expect(
      dashboard.content().getByRole('link', { name: newFlow, exact: true }),
    ).toBeVisible();
    await expect(
      dashboard.content().getByRole('button', { name: importCommand, exact: true }),
    ).toBeVisible();
    await expect(
      dashboard.flowViews().getByRole('link', { name: view, exact: true }),
    ).toBeVisible();
  },
);

Then(
  'la pagina non ha collegamenti a conti, storico, chiavi o notifiche',
  async ({ dashboard }) => {
    await expect(dashboard.flowViews()).toBeVisible();
    for (const area of OTHER_AREAS) {
      await expect(dashboard.content().locator(`a[href^="/dashboard/${area}"]`)).toHaveCount(0);
    }
  },
);

Then('compare il modulo di importazione di una strategia', async ({ dashboard }) => {
  await expect(dashboard.importForm()).toBeVisible();
  await expect(dashboard.importCommand()).toHaveAttribute('aria-expanded', 'true');
});

Then(
  'la pagina si intitola {string} e contiene la sezione delle chiavi dei fornitori IA',
  async ({ dashboard }, title: string) => {
    await expect(dashboard.pageHeading()).toHaveText(title);
    await expect(
      dashboard.content().getByRole('region', { name: 'Chiavi dei fornitori IA', exact: true }),
    ).toBeVisible();
  },
);
