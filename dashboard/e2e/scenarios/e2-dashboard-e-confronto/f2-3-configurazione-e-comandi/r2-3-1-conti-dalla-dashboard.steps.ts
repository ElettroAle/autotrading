import { expect } from '@playwright/test';

import { REJECTED_SECRET_KEY, fakePlatform } from '@/testing/mocks/platform';
import { formatAmount } from '@/utils/format-amount';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const ACCOUNTS_TITLE = 'I tuoi conti';
const VALID_ADDRESS = `0x${'a1'.repeat(20)}`;
const VALID_SECRET_KEY = `0x${'5e'.repeat(32)}`;
const OTHER_SECRET_KEY = `0x${'7c'.repeat(32)}`;
const REJECTED_ACCOUNT = 'rifiutato';
const CONFIRM_REMOVAL = 'Conferma la rimozione';
const REMOVAL_WITH_FLOWS = 'il conto ha flussi attivi o in pausa che verranno fermati: ';

// The user acting in a step is the one the background signed in on the page of the accounts.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

const registerAccount = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  name: string,
  secretKey: string,
): Promise<void> => {
  memory.secret = secretKey;
  const form = dashboard.page.getByRole('region', { name: 'Nuovo conto' });
  await dashboard.field('Nome', form).fill(name);
  await dashboard.field('Indirizzo del conto', form).fill(VALID_ADDRESS);
  await dashboard.field("Chiave dell'API wallet", form).fill(secretKey);
  await form.getByRole('button', { name: 'Registra il conto' }).click();
};

const accountOf = (account: string, name: string) =>
  fakePlatform.user(account).accounts.find((candidate) => candidate.name === name);

const reopenWithAccount = async (dashboard: DashboardPages, name: string): Promise<void> => {
  await dashboard.openAccounts();
  await expect(dashboard.accountRow(name)).toBeVisible();
};

// The removal is asked in a window first; the API decides whether it needs a second confirmation (ADR 0130).
const requestRemoval = async (dashboard: DashboardPages, name: string): Promise<void> => {
  await dashboard.accountRow(name).getByRole('button', { name: 'Rimuovi' }).click();
  await dashboard
    .confirmation(`Rimozione del conto ${name}`)
    .getByRole('button', { name: CONFIRM_REMOVAL })
    .click();
};

Given('che {string} è nella pagina dei conti', async ({ dashboard, memory }, account: string) => {
  memory.account = account;
  fakePlatform.addUser(account, { hasUserRole: true });
  await dashboard.openAccounts();
  await dashboard.signInAs(account);
  await expect(dashboard.pageHeading()).toHaveText(ACCOUNTS_TITLE);
});

Given('che {string} ha il conto {string}', async ({ dashboard }, account: string, name: string) => {
  fakePlatform.addAccount(account, name);
  await reopenWithAccount(dashboard, name);
});

Given(
  'che {string} ha il conto {string} senza flussi',
  async ({ dashboard }, account: string, name: string) => {
    const owned = fakePlatform.addAccount(account, name);
    expect(fakePlatform.operatingFlowsOf(fakePlatform.user(account), owned)).toEqual([]);
    await reopenWithAccount(dashboard, name);
  },
);

Given(
  'che il conto {string} ha il flusso attivo {string}',
  async ({ dashboard, memory }, name: string, flow: string) => {
    fakePlatform.addFlow(memory.account, flow, { accountName: name });
    await reopenWithAccount(dashboard, name);
  },
);

When(
  "{string} registra il conto {string} su testnet con indirizzo e chiave dell'API wallet validi",
  async ({ dashboard, memory }, account: string, name: string) => {
    expectSignedIn(memory, account);
    // The network of the accounts is the one of the installation: dev trades on the testnet (R0.2.1).
    await expect(dashboard.environment()).toHaveText('dev');
    await registerAccount(dashboard, memory, name, VALID_SECRET_KEY);
  },
);

When(
  "{string} registra un conto con una chiave che l'exchange rifiuta",
  async ({ dashboard, memory }, account: string) => {
    expectSignedIn(memory, account);
    memory.refusal = "credenziali rifiutate dall'exchange";
    await registerAccount(dashboard, memory, REJECTED_ACCOUNT, REJECTED_SECRET_KEY);
  },
);

When(
  '{string} sostituisce le credenziali del conto {string} con credenziali valide',
  async ({ dashboard, memory }, account: string, name: string) => {
    expectSignedIn(memory, account);
    memory.secret = OTHER_SECRET_KEY;
    const item = dashboard.accountRow(name);
    await item.getByRole('button', { name: 'Sostituisci le credenziali' }).click();
    await dashboard.field('Indirizzo del conto', item).fill(VALID_ADDRESS);
    await dashboard.field("Chiave dell'API wallet", item).fill(OTHER_SECRET_KEY);
    await item.getByRole('button', { name: 'Sostituisci', exact: true }).click();
  },
);

When(
  '{string} rimuove il conto {string} e conferma',
  async ({ dashboard, memory }, account: string, name: string) => {
    expectSignedIn(memory, account);
    await requestRemoval(dashboard, name);
  },
);

When(
  '{string} chiede di rimuovere il conto {string}',
  async ({ dashboard, memory }, account: string, name: string) => {
    expectSignedIn(memory, account);
    memory.subject = name;
    await requestRemoval(dashboard, name);
  },
);

Then(
  "il conto {string} compare nell'elenco con il suo saldo",
  async ({ dashboard }, name: string) => {
    const { balance } = fakePlatform.accountNamed(name);
    await expect(await dashboard.accountCell(name, 'Saldo')).toContainText(
      `${formatAmount(String(balance))} USDC`,
    );
  },
);

Then("il conto non compare nell'elenco", async ({ dashboard, memory }) => {
  expect(accountOf(memory.account, REJECTED_ACCOUNT)).toBeUndefined();
  await expect(dashboard.accountRow(REJECTED_ACCOUNT)).toHaveCount(0);
});

Then('la dashboard conferma la sostituzione', async ({ dashboard }) => {
  await expect(dashboard.message('Credenziali del conto principale sostituite')).toBeVisible();
});

Then(
  "il conto {string} non compare più nell'elenco",
  async ({ dashboard, memory }, name: string) => {
    await expect(dashboard.accountRow(name)).toHaveCount(0);
    expect(accountOf(memory.account, name)).toBeUndefined();
  },
);

Then(
  'la conferma dice che cosa accade al flusso {string} \\(R1.1.8)',
  async ({ dashboard, memory }, flow: string) => {
    await expect(dashboard.confirmation(`Rimozione del conto ${memory.subject}`)).toContainText(
      `${REMOVAL_WITH_FLOWS}${flow}`,
    );
  },
);
