import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

Given(
  'che {string} ha il ruolo Utente e il flusso {string}',
  async ({}, account: string, flow: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow);
  },
);

Given('che {string} ha il flusso {string}', async ({}, account: string, flow: string) => {
  fakePlatform.addUser(account, { hasUserRole: true });
  fakePlatform.addFlow(account, flow);
});

Given('che {string} non ha il ruolo Utente', async ({}, account: string) => {
  fakePlatform.addUser(account, { hasUserRole: false });
});

When(
  '{string} apre la dashboard ed entra con il proprio account',
  async ({ dashboard }, account: string) => {
    await dashboard.openAndSignInAs(account);
  },
);

Then('vede la pagina iniziale con il flusso {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
  await expect(dashboard.flows().getByRole('link', { name: flow })).toBeVisible();
});

Then('non vede il flusso {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.flows()).toBeVisible();
  await expect(dashboard.page.getByText(flow, { exact: true })).toHaveCount(0);
});

Then('non mostra alcun dato', async ({ dashboard }) => {
  await expect(dashboard.alert()).toBeVisible();
  await expect(dashboard.flows()).toHaveCount(0);
  await expect(dashboard.flowLinks()).toHaveCount(0);
});

When('un visitatore apre la dashboard senza entrare', async ({ dashboard }) => {
  await dashboard.open();
});

Then('viene portato/portata alla pagina di accesso', async ({ dashboard }) => {
  await expect(dashboard.signInHeading()).toBeVisible();
  await expect(dashboard.page).toHaveURL(/\/dashboard\/login(\?|$)/);
});

Given("che la dashboard è quella dell'installazione dev", async ({ dashboard }) => {
  const response = await dashboard.page.request.get('/dashboard/config.json');
  expect(await response.json()).toMatchObject({ environment: 'dev' });
});

When('{string} apre una qualsiasi pagina', async ({ dashboard, memory }, account: string) => {
  await dashboard.open();
  memory.environments.push((await dashboard.environment().textContent()) ?? '');
  await dashboard.signInAs(account);
  await expect(dashboard.flows()).toBeVisible();
  memory.environments.push((await dashboard.environment().textContent()) ?? '');
  await dashboard.flows().getByRole('link').first().click();
  await expect(dashboard.flowName()).toBeVisible();
  memory.environments.push((await dashboard.environment().textContent()) ?? '');
});

Then(
  "la pagina mostra l'indicazione {string}",
  async ({ dashboard, memory }, environment: string) => {
    await expect(dashboard.environment()).toHaveText(environment);
    expect(memory.environments).toEqual([environment, environment, environment]);
  },
);

Given("che l'accesso di {string} è scaduto", async ({ dashboard }, account: string) => {
  await dashboard.openAndSignInAs(account);
  await expect(dashboard.flows()).toBeVisible();
  fakePlatform.expireSessions();
  await dashboard.page.clock.fastForward('02:00:00');
});

When(
  '{string} apre la pagina del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    memory.account = account;
    await dashboard.openFlow(flow);
  },
);

Then(
  "dopo l'accesso torna alla pagina del flusso {string}",
  async ({ dashboard, memory }, flow: string) => {
    fakePlatform.restoreSessions();
    await dashboard.signInAs(memory.account);
    await expect(dashboard.page).toHaveURL(
      new URL(`/dashboard/flows/${fakePlatform.flowNamed(flow).id}`, dashboard.page.url()).href,
    );
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);
