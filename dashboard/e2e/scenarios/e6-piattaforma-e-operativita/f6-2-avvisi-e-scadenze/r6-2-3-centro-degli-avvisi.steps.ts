import { expect, type Locator } from '@playwright/test';

import { fakeAlerts, type FakeAlertKind, type FakeAlertResource } from '@/testing/mocks/alerts';
import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';

import type { DashboardPages } from '../../../support/dashboard-pages';
import type { ScenarioMemory } from '../../../support/fixtures';
import { Given, Then, When } from '../../../support/fixtures';

const HOUR = 60 * 60_000;
const ALERTS_PAGE = '/alerts';
const RESOLVED = "Niente: l'avviso è risolto.";

const hoursAgo = (hours: number): Date => new Date(Date.now() - hours * HOUR);

const tenantOf = (account: string): string => fakePlatform.user(account).tenantId;

const accountsOf = (account: string) =>
  fakePlatform.user(account).accounts.map(({ id, name, currency }) => ({ id, name, currency }));

const alertsOf = (account: string) => fakeAlerts.alertsOf(tenantOf(account), accountsOf(account));

const open = (
  account: string,
  kind: Exclude<FakeAlertKind, 'reconciliation_alarm'>,
  resource: FakeAlertResource,
  at = hoursAgo(1),
) => fakeAlerts.open(tenantOf(account), kind, resource, [], at);

const pauseOnItsOwn = (memory: ScenarioMemory, flow: string) => {
  const paused = fakePlatform.changeFlow(flow, { status: 'in pausa' });
  open(memory.account, 'flow_paused', { kind: 'flow', id: paused.id, name: flow });
};

const fillOf = (account: string, name: string, at?: Date) => {
  const { id } = fakePlatform.accountNamed(name);
  return open(account, 'unattributable_fill', { kind: 'account', id, name }, at);
};

const table = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('table', { name: 'Avvisi' });

const rows = (dashboard: DashboardPages): Locator => table(dashboard).locator('tbody tr');

const menuEntry = (dashboard: DashboardPages): Locator =>
  dashboard.page
    .getByRole('navigation', { name: 'Navigazione' })
    .getByRole('link', { name: /^Avvisi/ });

// A step before may have signed the user in already, on the page of the flow.
const openAlertsAs = async (dashboard: DashboardPages, account: string) => {
  await dashboard.open(ALERTS_PAGE);
  const heading = dashboard.page.getByRole('heading', { level: 1, name: 'Avvisi', exact: true });
  await expect(heading.or(dashboard.credentialsPage()).or(dashboard.signInButton())).toBeVisible();
  if (!(await heading.isVisible())) {
    await dashboard.signInAs(account);
  }
  await expect(dashboard.pageHeading()).toHaveText('Avvisi');
  await dashboard.waitUntilRead();
};

// The scenario has one alert: its detail is the only row of the list.
const openTheDetailAs = async (dashboard: DashboardPages, account: string) => {
  await openAlertsAs(dashboard, account);
  await rows(dashboard).first().getByRole('link').first().click();
  await expect(dashboard.pageHeading()).toHaveText('Avviso');
};

const whatToDo = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('region', { name: 'Che cosa fare' });

const confirm = async (dashboard: DashboardPages, command: string, confirmation: string) => {
  await whatToDo(dashboard).getByRole('button', { name: command }).click();
  await dashboard.confirmation(command).getByRole('button', { name: confirmation }).click();
};

Given(
  'che {string} ha il conto {string} con il flusso attivo {string}',
  async ({ memory }, account: string, name: string, flow: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, { accountName: name, status: 'attivo' });
    memory.account = account;
    memory.tradingAccount = name;
  },
);

Given('che sul conto {string} è aperto un allarme di riconciliazione', async ({}, name: string) => {
  fakeReconciliation.openAlarm(fakePlatform.accountNamed(name).id, 1000, 980, hoursAgo(2));
});

Given(
  "che sul conto {string} c'è un allarme di riconciliazione risolto",
  async ({}, name: string) => {
    fakeReconciliation.closedAlarm(fakePlatform.accountNamed(name).id, hoursAgo(3), hoursAgo(2));
  },
);

Given('che il flusso {string} è in pausa automatica', async ({ memory }, flow: string) => {
  pauseOnItsOwn(memory, flow);
});

Given(
  'che il flusso {string} è in pausa automatica con un avviso aperto',
  async ({ dashboard, memory }, flow: string) => {
    pauseOnItsOwn(memory, flow);
    await dashboard.openFlowAs(memory.account, flow);
  },
);

Given(
  "che sul conto {string} è aperto l'avviso di un'esecuzione senza identificativo della piattaforma",
  async ({ memory }, name: string) => {
    fillOf(memory.account, name);
  },
);

Given(
  'che {string} ha un avviso aperto e un avviso risolto',
  async ({ memory }, account: string) => {
    fillOf(account, memory.tradingAccount, hoursAgo(2));
    const resolved = fillOf(account, memory.tradingAccount, hoursAgo(1));
    fakeAlerts.resolveByHand(tenantOf(account), resolved.id, new Date());
  },
);

Given('che {string} ha un avviso aperto', async ({}, account: string) => {
  fakePlatform.ensureUser(account);
  const { id, name } = fakePlatform.addAccount(account, 'conto-di-bruno');
  open(account, 'unattributable_fill', { kind: 'account', id, name });
});

When('{string} apre la pagina Avvisi', async ({ dashboard }, account: string) => {
  await openAlertsAs(dashboard, account);
});

When(
  "{string} apre il dettaglio dell'avviso e conferma il saldo",
  async ({ dashboard }, account: string) => {
    await openTheDetailAs(dashboard, account);
    await confirm(dashboard, 'Conferma il saldo', 'Conferma la verifica');
  },
);

When("{string} segna l'avviso come risolto", async ({ dashboard }, account: string) => {
  await openTheDetailAs(dashboard, account);
  await confirm(dashboard, 'Segna come risolto', 'Conferma la risoluzione');
});

When("{string} apre il dettaglio dell'avviso", async ({ dashboard }, account: string) => {
  await openTheDetailAs(dashboard, account);
});

When(
  '{string} apre gli allarmi del conto {string} dal riquadro del conto',
  async ({ dashboard }, account: string, name: string) => {
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    // The reconciliation of the account is a tab of its page (ADR elenco-dei-conti-e-pagina-del-conto).
    await dashboard.openAccount(name, 'Riconciliazione');
    await dashboard.accountReconciliation(name).getByRole('link', { name: 'Allarmi' }).click();
    await expect(dashboard.pageHeading()).toHaveText('Avvisi');
  },
);

Then(
  'vede {int} avvisi aperti di gravità critica, uno con risorsa il conto {string} e uno con risorsa il flusso {string}',
  async ({ dashboard }, count: number, account: string, flow: string) => {
    await expect(rows(dashboard)).toHaveCount(count);
    await expect(rows(dashboard).filter({ hasText: 'Critica' })).toHaveCount(count);
    await expect(rows(dashboard).filter({ hasText: 'Aperto' })).toHaveCount(count);
    await expect(table(dashboard).getByRole('link', { name: `Conto ${account}` })).toBeVisible();
    await expect(table(dashboard).getByRole('link', { name: `Flusso ${flow}` })).toBeVisible();
  },
);

Then('la voce Avvisi del menu mostra {int}', async ({ dashboard }, count: number) => {
  await expect(menuEntry(dashboard)).toHaveText(`Avvisi ${count} aperti`);
});

Then('la voce Avvisi del menu non mostra alcun numero', async ({ dashboard }) => {
  await expect(menuEntry(dashboard)).toHaveText('Avvisi');
});

Then("l'avviso del flusso {string} è risolto", async ({ dashboard, memory }, flow: string) => {
  await expect(dashboard.flowCommand('pausa')).toBeVisible();
  const { id } = fakePlatform.flowNamed(flow);
  const pause = alertsOf(memory.account).find((alert) => alert.resource.id === id);
  expect(pause?.resolved_at).not.toBeNull();
});

Then("l'avviso è risolto", async ({ dashboard, memory }) => {
  await expect(whatToDo(dashboard)).toHaveText(new RegExp(RESOLVED));
  expect(alertsOf(memory.account).map((alert) => alert.resolved_at)).not.toContain(null);
  await expect(menuEntry(dashboard)).toHaveText('Avvisi');
});

Then("non c'è il comando per segnarlo come risolto", async ({ dashboard }) => {
  await expect(
    whatToDo(dashboard).getByRole('button', { name: 'Riprendi il flusso' }),
  ).toBeVisible();
  await expect(whatToDo(dashboard).getByRole('button', { name: 'Segna come risolto' })).toHaveCount(
    0,
  );
});

Then("c'è il comando per riprendere il flusso", async ({ dashboard }) => {
  await expect(
    whatToDo(dashboard).getByRole('button', { name: 'Riprendi il flusso' }),
  ).toBeVisible();
});

Then("vede solo l'avviso aperto", async ({ dashboard }) => {
  await expect(rows(dashboard)).toHaveCount(1);
  await expect(rows(dashboard)).toContainText('Aperto');
});

Then('scegliendo lo stato {string} vede entrambi', async ({ dashboard }, state: string) => {
  await dashboard.page
    .getByRole('group', { name: 'Filtri di Avvisi' })
    .getByRole('button', { name: new RegExp(`^${state}$`, 'i') })
    .click();
  await expect(rows(dashboard)).toHaveCount(2);
  await expect(rows(dashboard).filter({ hasText: 'Risolto il' })).toHaveCount(1);
});

Then(
  'vede gli avvisi filtrati per il conto {string} con tutti gli stati',
  async ({ dashboard, memory }, name: string) => {
    const { id } = fakePlatform.accountNamed(name);
    await expect(dashboard.page).toHaveURL(new RegExp(`/alerts\\?resource_id=${id}&state=all$`));
    await expect(rows(dashboard)).toHaveCount(1);
    await expect(rows(dashboard)).toContainText('Allarme di riconciliazione');
    await expect(rows(dashboard)).toContainText('Risolto il');
    expect(alertsOf(memory.account)).toHaveLength(1);
  },
);

Then("l'avviso di {string} non compare", async ({ dashboard }, account: string) => {
  const [theirs] = alertsOf(account);
  await expect(dashboard.page.getByText('Nessun avviso aperto')).toBeVisible();
  await expect(
    table(dashboard).getByRole('link', { name: `Conto ${theirs?.resource.name ?? ''}` }),
  ).toHaveCount(0);
});
