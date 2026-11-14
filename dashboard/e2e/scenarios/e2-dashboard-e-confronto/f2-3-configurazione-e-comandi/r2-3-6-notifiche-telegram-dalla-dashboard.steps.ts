import { expect } from '@playwright/test';

import { TEST_NOTIFICATION } from '@/testing/mocks/handlers';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const NOTIFICATIONS_TITLE = 'Notifiche Telegram';
const SEND_TEST = 'Invia notifica di prova';

// The user acting in a step is the one the background signed in on the page of the notifications.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

Given(
  'che {string} è nella pagina delle notifiche',
  async ({ dashboard, memory }, account: string) => {
    memory.account = account;
    fakePlatform.addUser(account, { hasUserRole: true });
    await dashboard.openNotifications();
    await dashboard.signInAs(account);
    await expect(dashboard.pageHeading()).toHaveText(NOTIFICATIONS_TITLE);
  },
);

// The chat sends the code to the bot outside the dashboard: the page shows it once read again.
Given(
  'che {string} ha collegato la chat {string}',
  async ({ dashboard }, account: string, chat: string) => {
    fakePlatform.linkChat(account, chat);
    await dashboard.openNotifications();
    await expect(dashboard.linkedChat()).toBeVisible();
  },
);

Given('che {string} non ha chat collegate', async ({}, account: string) => {
  fakePlatform.unlinkChat(account);
  expect(fakePlatform.linkedChatOf(account)).toBeUndefined();
});

When(
  '{string} chiede il codice di collegamento',
  async ({ dashboard, memory }, account: string) => {
    expectSignedIn(memory, account);
    await dashboard.button('Chiedi il codice di collegamento').click();
  },
);

When('{string} apre la pagina delle notifiche', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.openNotifications();
});

When('{string} invia una notifica di prova', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.button(SEND_TEST).click();
});

When('{string} scollega la chat e conferma', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.button('Scollega la chat').click();
  await dashboard.button('Conferma lo scollegamento').click();
});

Then(
  'la dashboard mostra il codice con la sua scadenza e il link del bot',
  async ({ dashboard, memory }) => {
    await expect(dashboard.linkCode()).toBeVisible();
    const issued = fakePlatform.linkCodeOf(memory.account);
    expect(issued).toBeDefined();
    await expect(dashboard.linkCode()).toHaveText(issued?.code ?? '');
    await expect(dashboard.linkCodeExpiry()).toHaveAttribute('datetime', issued?.expiresAt ?? '');
    await expect(dashboard.botLink()).toHaveAttribute('href', issued?.link ?? '');
  },
);

Then('la dashboard mostra la chat {string} come collegata', async ({ dashboard }, chat: string) => {
  await expect(dashboard.linkedChat()).toHaveText(
    `Chat Telegram ${fakePlatform.chatNamed(chat).id} collegata`,
  );
});

Then('la chat {string} riceve la notifica di prova', async ({}, chat: string) => {
  await expect.poll(() => fakePlatform.chatNamed(chat).received).toEqual([TEST_NOTIFICATION]);
});

Then("la dashboard conferma l'invio", async ({ dashboard }) => {
  await expect(dashboard.message('Notifica di prova inviata')).toBeVisible();
});

Then('il comando di prova non è disponibile', async ({ dashboard }) => {
  await expect(dashboard.pageHeading()).toHaveText(NOTIFICATIONS_TITLE);
  await expect(dashboard.button(SEND_TEST)).toHaveCount(0);
});
