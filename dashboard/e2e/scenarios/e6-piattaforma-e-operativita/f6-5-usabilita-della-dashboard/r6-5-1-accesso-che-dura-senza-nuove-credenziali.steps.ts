import { expect } from '@playwright/test';

import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

const FLOW = 'alfa';
const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;
// Longer than the life of an access token of the identity provider: the next call needs a new one. The clock jumps,
// so no rereading of the page starts on its own before the step that calls the API.
const PAST_THE_ACCESS_TOKEN = 2 * HOUR;

const later = (milliseconds: number): Date => new Date(Date.now() + milliseconds);
const MSAL_VERSION_KEY = 'msal.version';
const IDENTITY_PROVIDER_ORIGIN = new URL(FAKE_IDENTITY_PROVIDER.issuer).origin;

/** The directives of a content security policy, by name. */
const directivesOf = (policy: string): Map<string, string> =>
  new Map(
    policy.split(';').map((directive) => {
      const [name = '', ...sources] = directive.trim().split(/\s+/);
      return [name, sources.join(' ')];
    }),
  );

const policyOf = (headers: Record<string, string> | undefined): Map<string, string> =>
  directivesOf(headers?.['content-security-policy'] ?? '');

Given(
  "che {string} ha fatto l'accesso alla dashboard e la sua sessione Entra è valida",
  async ({ dashboard, memory }, account: string) => {
    memory.account = account;
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, FLOW);
    await dashboard.openAndSignInAs(account);
    await expect(dashboard.flows()).toBeVisible();
    expect(fakePlatform.identityProviderSession()).toBe(account);
    memory.credentialPages = fakePlatform.credentialPagesShown();
  },
);

Given('che {string} chiude il browser', async ({ browserRestart }, account: string) => {
  await browserRestart.close();
  // Closing the browser leaves the session at the identity provider as it was.
  expect(fakePlatform.identityProviderSession()).toBe(account);
});

When('riapre la dashboard il giorno dopo', async ({ browserRestart }) => {
  const reopened = await browserRestart.reopenAt(later(DAY));
  await reopened.open();
});

Then('vede i suoi flussi senza inserire le credenziali', async ({ browserRestart, memory }) => {
  const reopened = browserRestart.reopened();
  await expect(reopened.flows().getByRole('link', { name: FLOW, exact: true })).toBeVisible();
  expect(fakePlatform.credentialPagesShown()).toBe(memory.credentialPages);
  // The tokens outlived the browser in the local storage: not even a redirect to the identity provider.
  expect(reopened.redirectsToIdentityProvider()).toBe(0);
});

Given(
  'che il refresh token di {string} è scaduto',
  async ({ dashboard, memory }, account: string) => {
    await dashboard.flows().getByRole('link', { name: FLOW, exact: true }).click();
    await expect(dashboard.flowName()).toHaveText(FLOW);
    await dashboard.waitUntilRead();
    fakePlatform.expireRefreshTokens();
    // Only the refresh token expires: the session at the identity provider lives on.
    expect(fakePlatform.identityProviderSession()).toBe(account);
    await dashboard.page.clock.setSystemTime(later(PAST_THE_ACCESS_TOKEN));
    memory.signInRedirects = dashboard.redirectsToIdentityProvider();
  },
);

When("la dashboard chiama l'API", async ({ dashboard }) => {
  await dashboard.button('Aggiorna').click();
});

Then(
  'la dashboard rinnova i token con un redirect a Entra senza chiedere le credenziali',
  async ({ dashboard, memory }) => {
    await expect
      .poll(() => dashboard.redirectsToIdentityProvider())
      .toBe(memory.signInRedirects + 1);
    await expect(dashboard.flowName()).toHaveText(FLOW);
    expect(fakePlatform.credentialPagesShown()).toBe(memory.credentialPages);
  },
);

Then(
  'torna alla pagina in cui {string} si trovava',
  async ({ dashboard, memory }, account: string) => {
    expect(account).toBe(memory.account);
    await expect(dashboard.page).toHaveURL(
      new URL(`/dashboard/flows/${fakePlatform.flowNamed(FLOW).id}`, dashboard.page.url()).href,
    );
    await expect(dashboard.flowName()).toHaveText(FLOW);
  },
);

Given('che la sessione Entra di {string} è finita', async ({ dashboard }, account: string) => {
  expect(fakePlatform.identityProviderSession()).toBe(account);
  fakePlatform.expireSessions();
  await dashboard.page.clock.setSystemTime(later(PAST_THE_ACCESS_TOKEN));
});

Then('Entra le chiede le credenziali', async ({ memory }) => {
  expect(fakePlatform.credentialPagesShown()).toBeGreaterThan(memory.credentialPages);
});

When('{string} sceglie «Esci»', async ({ dashboard }, account: string) => {
  expect(fakePlatform.identityProviderSession()).toBe(account);
  // «Esci» is in the menu of the user, on top of the page (ADR area-utente-in-alto-a-destra).
  await dashboard.page
    .getByRole('banner')
    .getByRole('button', { name: account, exact: true })
    .click();
  await dashboard.page.getByRole('menuitem', { name: 'Esci' }).click();
  await expect(dashboard.signInHeading()).toBeVisible();
});

Then('nel browser non resta alcun token né dato di sessione', async ({ dashboard }) => {
  const storage = await dashboard.page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }));
  // MSAL marks the local storage with the version of its library at every start: no token, no data of the user.
  expect(storage).toEqual({ local: [MSAL_VERSION_KEY], session: [] });
  expect(
    await dashboard.page.evaluate((key) => localStorage.getItem(key), MSAL_VERSION_KEY),
  ).toMatch(/^\d+\.\d+\.\d+$/);
  expect(fakePlatform.identityProviderSession()).toBeUndefined();
});

Then('riaprendo la dashboard le vengono chieste le credenziali', async ({ dashboard }) => {
  await dashboard.open();
  await expect(dashboard.credentialsPage()).toBeVisible();
});

When('il browser carica una pagina della dashboard', async ({ dashboard, memory }) => {
  await dashboard.page.exposeFunction('reportPolicyViolation', (violation: string) => {
    memory.policyViolations.push(violation);
  });
  await dashboard.page.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', (event) => {
      const report = (window as unknown as { reportPolicyViolation: (text: string) => void })
        .reportPolicyViolation;
      report(`${event.violatedDirective} ${event.blockedURI}`);
    });
  });
  // The page of a flow draws its equity curve: the styles of the charts are under the policy too.
  const response = await dashboard.page.goto(`/dashboard/flows/${fakePlatform.flowNamed(FLOW).id}`);
  memory.loadedPage = {
    headers: (await response?.allHeaders()) ?? {},
    body: (await response?.text()) ?? '',
  };
  await expect(dashboard.flowName()).toHaveText(FLOW);
  await dashboard.waitUntilRead();
});

Then(
  'la risposta porta una Content Security Policy che ammette script e stili solo dalla propria origine',
  async ({ memory }) => {
    const policy = policyOf(memory.loadedPage?.headers);
    expect(policy.get('default-src')).toBe("'none'");
    expect(policy.get('script-src')).toBe("'self'");
    expect(policy.get('style-src')).toBe("'self'");
  },
);

Then("connessioni solo verso l'API e Entra, senza script inline né frame", async ({ memory }) => {
  const policy = policyOf(memory.loadedPage?.headers);
  // The API answers on the origin of the dashboard (ADR 0117).
  expect(policy.get('connect-src')).toBe(`'self' ${IDENTITY_PROVIDER_ORIGIN}`);
  expect(policy.get('frame-src')).toBe("'none'");
  expect(policy.get('frame-ancestors')).toBe("'none'");
  expect(memory.loadedPage?.headers['content-security-policy']).not.toContain('unsafe-inline');
  // The build has no script nor style inside the page: every one is a file of the dashboard.
  expect(memory.loadedPage?.body).not.toMatch(/<script(?![^>]*\ssrc=)[^>]*>/);
  expect(memory.loadedPage?.body).not.toMatch(/<style[\s>]/);
  expect(memory.policyViolations).toEqual([]);
});
