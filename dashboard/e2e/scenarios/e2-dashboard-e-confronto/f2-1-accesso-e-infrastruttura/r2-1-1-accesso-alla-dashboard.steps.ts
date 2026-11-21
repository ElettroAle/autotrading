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
  await expect(dashboard.warning('Accesso non consentito: manca il ruolo Utente')).toBeVisible();
  await expect(dashboard.flows()).toHaveCount(0);
  await expect(dashboard.flowLinks()).toHaveCount(0);
});

When('un visitatore apre la dashboard senza entrare', async ({ dashboard }) => {
  await dashboard.open();
});

// The dashboard sends the visitor straight to the identity provider, which asks the credentials
// (ADR accesso-persistente-con-cache-msal-in-localstorage).
Then('viene portato/portata alla pagina di accesso', async ({ dashboard }) => {
  await expect(dashboard.credentialsPage()).toBeVisible();
  await expect(dashboard.page).toHaveURL(/^https:\/\/login\.fake-idp\.test\//);
});

Given("che la dashboard è quella dell'installazione dev", async ({ dashboard }) => {
  const response = await dashboard.page.request.get('/dashboard/config.json');
  expect(await response.json()).toMatchObject({ environment: 'dev' });
});

When('{string} apre una qualsiasi pagina', async ({ dashboard, memory }, account: string) => {
  await dashboard.openAndSignInAs(account);
  await expect(dashboard.flows()).toBeVisible();
  memory.environments.push((await dashboard.environment().textContent()) ?? '');
  await dashboard.flows().getByRole('link').first().click();
  await expect(dashboard.flowName()).toBeVisible();
  memory.environments.push((await dashboard.environment().textContent()) ?? '');
  await dashboard.open('/login');
  await expect(dashboard.signInHeading()).toBeVisible();
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
  // The clock jumps past the access token: no rereading of the page starts the sign-in before the user opens a page.
  await dashboard.page.clock.setSystemTime(new Date(Date.now() + 2 * 60 * 60 * 1000));
});

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

// The tenant of a first access is born empty on the API (R0.1.2): the dashboard opens on it without an error.
Given(
  'che {string} ha il ruolo Utente e non ha mai usato la piattaforma',
  async ({}, account: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
  },
);

Then('vede la pagina iniziale senza flussi', async ({ dashboard }) => {
  await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
  await expect(dashboard.page.getByText('Non hai ancora flussi.')).toBeVisible();
  await expect(dashboard.page.getByRole('alert')).toHaveCount(0);
  await expect(dashboard.flows()).toHaveCount(0);
});
