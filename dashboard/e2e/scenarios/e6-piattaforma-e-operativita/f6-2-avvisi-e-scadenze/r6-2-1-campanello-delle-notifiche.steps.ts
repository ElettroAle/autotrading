import { expect, type Locator } from '@playwright/test';

import { fakeInbox, flowTarget } from '@/testing/mocks/notification-inbox';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

const MINUTE = 60_000;
const PAUSED_TITLE = 'Flusso alfa in pausa';
const OTHER_TITLE = 'beta: ciclo fallito';

const tenantOf = (account: string): string => fakePlatform.user(account).tenantId;

const minutesAgo = (minutes: number): Date => new Date(Date.now() - minutes * MINUTE);

const bell = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('banner').getByRole('button', { name: /^Notifiche,/ });

const panel = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('dialog', { name: 'Notifiche' });

const unreadMark = (dashboard: DashboardPages): Locator =>
  bell(dashboard).getByTestId('unread-count');

// The bell is page data: the dashboard reads it again with the page (R2.1.2).
const reread = async (dashboard: DashboardPages) => {
  await dashboard.button('Aggiorna').click();
  await dashboard.waitUntilRead();
};

const openTheBell = async (dashboard: DashboardPages) => {
  await reread(dashboard);
  await bell(dashboard).click();
  await expect(panel(dashboard)).toBeVisible();
  await dashboard.waitUntilRead();
};

Given('che {string} è nella dashboard', async ({ dashboard, memory }, account: string) => {
  fakePlatform.ensureUser(account);
  memory.account = account;
  await dashboard.openAndSignInAs(account);
  await expect(bell(dashboard)).toBeVisible();
  await dashboard.waitUntilRead();
});

Given('che {string} ha {int} notifiche non lette', async ({}, account: string, count: number) => {
  Array.from({ length: count }, (_, index) =>
    fakeInbox.notify(
      tenantOf(account),
      { title: `flusso-${index}: ciclo fallito`, text: 'Errore: timeout' },
      minutesAgo(count - index),
    ),
  );
});

Given(
  'che {string} ha la notifica {string}',
  async ({ memory }, account: string, title: string) => {
    expect(title).toBe(PAUSED_TITLE);
    const flow = fakePlatform.addFlow(account, 'alfa');
    memory.flow = flow.name;
    fakeInbox.notify(
      tenantOf(account),
      { title: 'alfa: in pausa', text: 'Motivo: credito esaurito', targets: [flowTarget(flow.id)] },
      minutesAgo(1),
    );
  },
);

Given('che {string} non ha collegato Telegram', async ({}, account: string) => {
  expect(fakePlatform.linkedChatOf(account)).toBeUndefined();
});

Given('che {string} ha una notifica', async ({}, account: string) => {
  fakePlatform.ensureUser(account);
  fakeInbox.notify(tenantOf(account), { title: OTHER_TITLE }, minutesAgo(1));
});

When(
  '{string} guarda il campanello accanto al suo nome',
  async ({ dashboard, memory }, account: string) => {
    // The user who looks is the one in the dashboard.
    expect(account).toBe(memory.account);
    await reread(dashboard);
  },
);

When(
  '{string} apre il campanello e sceglie la notifica',
  async ({ dashboard, memory }, account: string) => {
    // The user who looks is the one in the dashboard.
    expect(account).toBe(memory.account);
    await openTheBell(dashboard);
    await panel(dashboard)
      .getByRole('button', { name: /alfa: in pausa/ })
      .click();
  },
);

When('la piattaforma genera una notifica per {string}', async ({ memory }, account: string) => {
  memory.subject = 'gamma: ciclo fallito';
  fakeInbox.notify(tenantOf(account), { title: memory.subject }, minutesAgo(1));
});

When('{string} le segna tutte come lette', async ({ dashboard, memory }, account: string) => {
  // The user who looks is the one in the dashboard.
  expect(account).toBe(memory.account);
  await openTheBell(dashboard);
  await panel(dashboard).getByRole('button', { name: 'Segna tutte come lette' }).click();
  await dashboard.waitUntilRead();
});

When('{string} apre il campanello', async ({ dashboard, memory }, account: string) => {
  // The user who looks is the one in the dashboard.
  expect(account).toBe(memory.account);
  await openTheBell(dashboard);
});

Then('il campanello mostra {int}', async ({ dashboard }, count: number) => {
  await expect(bell(dashboard)).toHaveAccessibleName(`Notifiche, ${count} non lette`);
  await expect(unreadMark(dashboard)).toHaveText(String(count));
});

Then(
  'la dashboard apre la pagina del flusso {string} e la notifica è letta',
  async ({ dashboard, memory }, flow: string) => {
    const { id } = fakePlatform.flowNamed(flow);
    await expect(dashboard.page).toHaveURL(new RegExp(`/dashboard/flows/${id}$`));
    await expect(dashboard.flowName()).toHaveText(flow);
    await expect
      .poll(() => fakeInbox.notificationsOf(tenantOf(memory.account))[0]?.read_at ?? null)
      .not.toBeNull();
    await expect(unreadMark(dashboard)).toHaveCount(0);
  },
);

Then('la notifica compare nel campanello', async ({ dashboard, memory }) => {
  await openTheBell(dashboard);
  await expect(panel(dashboard).getByRole('listitem')).toHaveCount(1);
  await expect(panel(dashboard).getByRole('listitem')).toContainText(memory.subject);
});

Then('il campanello non mostra alcun numero', async ({ dashboard, memory }) => {
  await expect(bell(dashboard)).toHaveAccessibleName('Notifiche, 0 non lette');
  await expect(unreadMark(dashboard)).toHaveCount(0);
  expect(fakeInbox.unreadCount(tenantOf(memory.account))).toBe(0);
});

Then('la notifica di {string} non compare', async ({ dashboard }, account: string) => {
  await expect(panel(dashboard).getByText('Nessuna notifica')).toBeVisible();
  await expect(panel(dashboard).getByText(OTHER_TITLE)).toHaveCount(0);
  expect(fakeInbox.notificationsOf(tenantOf(account)).map(({ title }) => title)).toEqual([
    OTHER_TITLE,
  ]);
});
