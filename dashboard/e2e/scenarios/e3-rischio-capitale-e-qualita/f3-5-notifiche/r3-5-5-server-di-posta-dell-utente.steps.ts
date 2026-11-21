import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// R3.5.5 on the page of the notifications: it opens on the channels while none is linked (ADR pagina-notifiche-a-schede);
// pytest-bdd runs every scenario of the mail server on the use cases.

const SUBMISSION_PORT = 587;

Given(
  "che {string} ha indicato l'indirizzo {string} per le notifiche",
  ({}, account: string, address: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.setNotificationEmail(account, address);
  },
);

Given(
  'che {string} ha salvato il server di posta {string}',
  ({}, account: string, host: string) => {
    fakePlatform.saveMailServer(account, {
      host,
      port: SUBMISSION_PORT,
      security: 'STARTTLS',
      username: `${account}@example.com`,
      sender: '',
      password: 'password-per-le-app',
    });
  },
);

Given('che {string} non ha collegato alcun canale', ({}, account: string) => {
  fakePlatform.ensureUser(account);
  expect(fakePlatform.linkedChatOf(account)).toBeUndefined();
  expect(fakePlatform.mailServerOf(account)).toBeUndefined();
});

When('{string} apre la pagina Notifiche', async ({ dashboard, memory }, account: string) => {
  memory.account = account;
  await dashboard.open('/notifications');
  await dashboard.signInAs(account);
});

Then(
  'la pagina Notifiche ha le schede {string} e {string} e mostra {string}',
  async ({ dashboard }, first: string, second: string, shown: string) => {
    const tabs = dashboard.page
      .getByRole('tablist', { name: 'Viste delle notifiche' })
      .getByRole('tab');
    // The tab of the channels counts those still to configure beside its name.
    await expect(tabs).toHaveText([first, new RegExp(`^${second}( \\(\\d\\))?$`)]);
    await expect(tabs.filter({ hasText: new RegExp(`^${shown}`) })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  },
);
