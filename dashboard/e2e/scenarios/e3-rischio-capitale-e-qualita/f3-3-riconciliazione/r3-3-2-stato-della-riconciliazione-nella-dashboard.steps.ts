import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { formatInstant } from '@/utils/format-instant';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

const RECONCILIATION = 'Riconciliazione';
const CONFIRM = 'Ho verificato';
const HOUR = 60 * 60_000;
const DAY = 24 * HOUR;
// The balances of an alarm the scenario does not detail.
const EXPECTED = 1000;
const READ = 980;

const accountIdOf = (name: string): string => fakePlatform.accountNamed(name).id;

/** The reconciliation of the account on the page of the accounts, in its column. */
const reconciliationOf = (dashboard: DashboardPages, name: string): Promise<Locator> =>
  dashboard.accountCell(name, RECONCILIATION);

/** One value of the reconciliation of the account, by the term it shows. */
const detailOf = async (dashboard: DashboardPages, name: string, term: string) =>
  (await reconciliationOf(dashboard, name)).getByLabel(term, { exact: true });

const openAccountsAs = async (dashboard: DashboardPages, account: string): Promise<void> => {
  await dashboard.openAccounts();
  await dashboard.signInAs(account);
};

// The confirmation is asked in a window, which the user confirms or cancels (ADR stato-della-riconciliazione-nella-
// dashboard).
const chooseConfirmation = async (
  dashboard: DashboardPages,
  account: string,
  name: string,
  answer: string,
): Promise<void> => {
  await openAccountsAs(dashboard, account);
  const reconciliation = await reconciliationOf(dashboard, name);
  await reconciliation.getByRole('button', { name: CONFIRM }).click();
  await dashboard
    .confirmation(`Verifica del conto ${name}`)
    .getByRole('button', { name: answer, exact: true })
    .click();
};

Given(
  'che {string} ha il conto {string} con il flusso {string} e soglia di scostamento {int}%',
  async ({ memory }, account: string, name: string, flow: string, threshold: number) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, { accountName: name });
    expect(fakeReconciliation.setThreshold(accountIdOf(name), String(threshold))).toBe(true);
    memory.account = account;
    memory.tradingAccount = name;
  },
);

Given(
  "che l'ultimo confronto del conto {string} ha saldo atteso {int} USDC e saldo letto {int} USDC",
  async ({}, name: string, expected: number, read: number) => {
    fakeReconciliation.compare(accountIdOf(name), expected, read, new Date(Date.now() - HOUR));
  },
);

Given(
  "che sul conto {string} c'è un allarme di riconciliazione con saldo atteso {int} USDC e saldo letto {int} USDC",
  async ({}, name: string, expected: number, read: number) => {
    fakeReconciliation.openAlarm(accountIdOf(name), expected, read, new Date(Date.now() - HOUR));
  },
);

Given("che sul conto {string} c'è un allarme di riconciliazione", async ({}, name: string) => {
  fakeReconciliation.openAlarm(accountIdOf(name), EXPECTED, READ, new Date(Date.now() - HOUR));
});

Given(
  'che il conto {string} ha un allarme chiuso ieri e un allarme aperto oggi',
  async ({}, name: string) => {
    const now = Date.now();
    fakeReconciliation.closedAlarm(
      accountIdOf(name),
      new Date(now - DAY),
      new Date(now - DAY + HOUR),
    );
    fakeReconciliation.openAlarm(accountIdOf(name), EXPECTED, READ, new Date(now - HOUR));
  },
);

When(
  '{string} sceglie {string} sul conto {string} e conferma',
  async ({ dashboard }, account: string, command: string, name: string) => {
    expect(command).toBe(CONFIRM);
    await chooseConfirmation(dashboard, account, name, 'Conferma la verifica');
  },
);

When(
  '{string} sceglie {string} sul conto {string} e annulla',
  async ({ dashboard }, account: string, command: string, name: string) => {
    expect(command).toBe(CONFIRM);
    await chooseConfirmation(dashboard, account, name, 'Annulla');
  },
);

When(
  '{string} apre gli allarmi del conto {string}',
  async ({ dashboard }, account: string, name: string) => {
    await openAccountsAs(dashboard, account);
    await (await reconciliationOf(dashboard, name)).getByRole('link', { name: 'Allarmi' }).click();
    await expect(dashboard.pageHeading()).toHaveText(`Allarmi del conto ${name}`);
  },
);

When(
  '{string} imposta dalla pagina del conto {string} la soglia di scostamento a {int}%',
  async ({ dashboard }, account: string, name: string, threshold: number) => {
    await openAccountsAs(dashboard, account);
    const reconciliation = await reconciliationOf(dashboard, name);
    await reconciliation.getByRole('button', { name: 'Modifica la soglia' }).click();
    await dashboard.field('Soglia di scostamento (%)', reconciliation).fill(String(threshold));
    await reconciliation.getByRole('button', { name: 'Salva la soglia' }).click();
  },
);

Then(
  "il conto {string} mostra lo stato {string} con data e ora dell'ultimo confronto",
  async ({ dashboard }, name: string, state: string) => {
    const comparedAt = fakeReconciliation.statusOf(accountIdOf(name)).last_comparison?.compared_at;
    expect(comparedAt).toBeDefined();
    await expect(await detailOf(dashboard, name, 'Stato')).toHaveText(state);
    await expect(await detailOf(dashboard, name, 'Ultimo confronto')).toHaveText(
      formatInstant(comparedAt ?? ''),
    );
  },
);

Then(
  'il conto {string} mostra lo stato {string} con saldo atteso {int} USDC, saldo letto {int} USDC, scostamento {int}% e soglia {int}%',
  async (
    { dashboard },
    name: string,
    state: string,
    expected: number,
    read: number,
    deviation: number,
    threshold: number,
  ) => {
    await expect(await detailOf(dashboard, name, 'Stato')).toHaveText(state);
    await expect(await detailOf(dashboard, name, 'Saldo atteso')).toHaveText(`${expected} USDC`);
    await expect(await detailOf(dashboard, name, 'Saldo letto')).toHaveText(`${read} USDC`);
    await expect(await detailOf(dashboard, name, 'Scostamento')).toHaveText(`${deviation}%`);
    await expect(await detailOf(dashboard, name, 'Soglia')).toHaveText(`${threshold}%`);
  },
);

Then(
  'il conto {string} offre il comando {string}',
  async ({ dashboard }, name: string, command: string) => {
    await expect(
      (await reconciliationOf(dashboard, name)).getByRole('button', { name: command }),
    ).toBeVisible();
  },
);

Then(
  'il conto {string} mostra lo stato {string}',
  async ({ dashboard }, name: string, state: string) => {
    await expect(await detailOf(dashboard, name, 'Stato')).toHaveText(state);
    expect(fakeReconciliation.statusOf(accountIdOf(name)).aligned).toBe(state === 'allineato');
  },
);

Then(
  "l'elenco mostra prima l'allarme di oggi, aperto, poi quello di ieri con data e ora della conferma",
  async ({ dashboard, memory }) => {
    const rows = dashboard.page
      .getByRole('table', { name: 'Allarmi di riconciliazione' })
      .locator('tbody tr');
    const [today, yesterday] = fakeReconciliation.alarmsOf(accountIdOf(memory.tradingAccount));
    await expect(rows).toHaveCount(2);
    await expect(dashboard.cell(rows.nth(0), 'Aperto il')).toContainText(
      formatInstant(today?.opened_at ?? ''),
    );
    await expect(dashboard.cell(rows.nth(0), 'Stato')).toContainText('aperto');
    await expect(dashboard.cell(rows.nth(1), 'Aperto il')).toContainText(
      formatInstant(yesterday?.opened_at ?? ''),
    );
    await expect(dashboard.cell(rows.nth(1), 'Confermato il')).toContainText(
      formatInstant(yesterday?.confirmed_at ?? ''),
    );
  },
);

Then(
  'il conto {string} mostra la soglia {int}%',
  async ({ dashboard }, name: string, threshold: number) => {
    await expect(await detailOf(dashboard, name, 'Soglia')).toHaveText(`${threshold}%`);
    expect(fakeReconciliation.thresholdOf(accountIdOf(name))).toBe(String(threshold));
  },
);
