import { expect } from '@playwright/test';

import {
  aHistoryCycle,
  aHistoryOrder,
  aHistoryPosition,
  anExecution,
  type FakeOwner,
} from '@/testing/mocks/history';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const YEAR = 2026;
// Months of a JavaScript date count from 0.
const NOVEMBER_INDEX = 10;
const DAYS_OF_NOVEMBER = 30;

/** A day of November at 11:00 UTC, noon in Italy: the day the page shows is the same in both. */
const dayOfNovember = (day: number): Date => new Date(Date.UTC(YEAR, NOVEMBER_INDEX, day, 11));

const shownDay = (day: number): string => `${String(day).padStart(2, '0')}/11/${YEAR}`;

const isoDay = (day: number): string => `${YEAR}-11-${String(day).padStart(2, '0')}`;

/** The configuration version of the flow in force on the day: the scenario remembers from when the second holds. */
const ownerOn = (memory: ScenarioMemory, owner: FakeOwner, day: number): FakeOwner => ({
  ...owner,
  version: day < memory.secondVersionFrom ? 1 : 2,
});

const ownerOf = (account: string, flow: string): FakeOwner => {
  const owned = fakePlatform.flowNamed(flow);
  const accountName = fakePlatform
    .user(account)
    .accounts.find((candidate) => candidate.id === owned.accountId)?.name;
  return {
    flowId: owned.id,
    flow,
    accountId: owned.accountId ?? '',
    account: accountName ?? '',
    version: owned.version,
  };
};

// The search is in the address of the page: the user signs in and comes back to it with its filters.
const openHistoryAs = async (
  dashboard: DashboardPages,
  account: string,
  search = '',
): Promise<void> => {
  await dashboard.openHistory(search);
  await dashboard.signInAs(account);
  await expect(dashboard.historyTab('Cicli')).toBeVisible();
};

Given(
  /^che "([^"]+)" ha il flusso "([^"]+)" sul conto "([^"]+)" con cicli dal (\d+)° al (\d+) novembre e la versione 2 in vigore dal (\d+) novembre$/,
  async (
    { memory },
    account: string,
    flow: string,
    accountName: string,
    first: string,
    last: string,
    since: string,
  ) => {
    fakePlatform.giveFlowTo(account, flow);
    const { id } = fakePlatform.addAccount(account, accountName);
    fakePlatform.changeFlow(flow, { accountId: id, assets: [], version: 2 });
    memory.account = account;
    memory.secondVersionFrom = Number(since);
    const owner = ownerOf(account, flow);
    for (let day = Number(first); day <= Number(last); day += 1) {
      fakePlatform
        .recordsOf(account)
        .cycles.push(aHistoryCycle(ownerOn(memory, owner, day), dayOfNovember(day), []));
    }
  },
);

Given(
  'che il flusso {string} ha ordini e posizioni chiuse su {string} e {string}',
  async ({ memory }, flow: string, first: string, second: string) => {
    const assets = [first, second];
    fakePlatform.changeFlow(flow, { assets });
    const owner = ownerOf(memory.account, flow);
    const records = fakePlatform.recordsOf(memory.account);
    for (let day = 1; day <= DAYS_OF_NOVEMBER; day += 1) {
      const dayOwner = ownerOn(memory, owner, day);
      const at = dayOfNovember(day);
      for (const asset of assets) {
        records.closedPositions.push(aHistoryPosition(dayOwner, asset, at));
        records.orders.push(
          aHistoryOrder(dayOwner, asset, at, [
            anExecution(at, '91000.5', '0.015', '0.41'),
            anExecution(at, '91001', '0.005', '0.14'),
          ]),
        );
      }
    }
  },
);

When(
  '{string} interroga i cicli del flusso {string} con la versione {int}',
  async ({ dashboard }, account: string, flow: string, version: number) => {
    await openHistoryAs(dashboard, account);
    await dashboard.filter('Flusso').selectOption({ label: flow });
    await dashboard.filter('Versione').selectOption({ label: `Versione ${version}` });
  },
);

When(
  '{string} interroga le posizioni chiuse con asset {string} dal {int} al {int} novembre',
  async ({ dashboard }, account: string, asset: string, first: number, last: number) => {
    await openHistoryAs(dashboard, account);
    await dashboard.historyTab('Posizioni chiuse').click();
    await dashboard.filter('Asset').selectOption({ label: asset });
    await dashboard.period().selectOption({ label: 'Intervallo' });
    await dashboard.filter('Dal').fill(isoDay(first));
    await dashboard.filter('Al').fill(isoDay(last));
  },
);

When(
  '{string} interroga gli ordini del conto {string}',
  async ({ dashboard }, account: string, accountName: string) => {
    await openHistoryAs(dashboard, account);
    await dashboard.historyTab('Ordini').click();
    await dashboard.filter('Conto').selectOption({ label: accountName });
  },
);

// The page offers a version only with its flow: a search without the flow reaches the API only through a link.
When(
  '{string} interroga i cicli con la versione {int} senza indicare un flusso',
  async ({ dashboard }, account: string, version: number) => {
    await openHistoryAs(dashboard, account, `?version=${version}`);
  },
);

// The user has no flow that trades the asset, so the filter is not among those offered: the link carries it.
When(
  '{string} interroga le posizioni chiuse con asset {string}',
  async ({ dashboard }, account: string, asset: string) => {
    await openHistoryAs(dashboard, account, `?tab=closed-positions&asset=${asset}`);
  },
);

Then('ottiene solo i cicli dal {int} novembre in poi', async ({ dashboard }, since: number) => {
  const rows = dashboard.historyRows('Cicli');
  await expect(rows).toHaveCount(DAYS_OF_NOVEMBER - since + 1);
  await expect(rows.first()).toContainText(shownDay(DAYS_OF_NOVEMBER));
  await expect(rows.last()).toContainText(shownDay(since));
  await expect(rows.locator('td:nth-child(3)')).toHaveText(
    Array.from({ length: DAYS_OF_NOVEMBER - since + 1 }, () => /Versione\s*2$/),
  );
});

Then(
  'ottiene solo le posizioni su {string} chiuse in quel periodo',
  async ({ dashboard }, asset: string) => {
    const rows = dashboard.historyRows('Posizioni chiuse');
    await expect(rows).toHaveCount(11);
    await expect(rows.first()).toContainText(shownDay(20));
    await expect(rows.last()).toContainText(shownDay(10));
    for (const row of await rows.all()) {
      await expect(row).toContainText(asset);
    }
  },
);

Then(
  'ogni ordine mostra le sue esecuzioni con prezzo, quantità e commissioni',
  async ({ dashboard }) => {
    const rows = dashboard.historyRows('Ordini');
    await expect(rows).toHaveCount(50);
    for (const row of await rows.all()) {
      await expect(row).toContainText('principale');
      await row.getByText('2 esecuzioni').click();
      const executions = row.getByRole('table', { name: 'Esecuzioni' }).locator('tbody tr');
      await expect(executions).toHaveCount(2);
      await expect(executions.first().locator('td')).toHaveText([
        /\d/,
        '91.000,5',
        '0.015',
        '0,41',
      ]);
      await expect(executions.last().locator('td')).toHaveText([/\d/, '91.001', '0.005', '0,14']);
    }
  },
);

Then(
  "l'interrogazione è rifiutata con il motivo {string}",
  async ({ dashboard }, reason: string) => {
    await expect(dashboard.alert()).toHaveText(`Interrogazione rifiutata: ${reason}`);
  },
);

Then('non ottiene alcuna posizione del flusso {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.page.getByText('Nessuna posizione chiusa trovata.')).toBeVisible();
  await expect(dashboard.historyRows('Posizioni chiuse').filter({ hasText: flow })).toHaveCount(0);
});
