import { expect } from '@playwright/test';

import { fakePlatform, versionsWith } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const DATE_AND_TIME = /^\d{1,2} \S+ \d{4}, \d{2}:\d{2}$/;

Given(
  'che il flusso {string} ha {int} versioni e tra la {int} e la {int} è cambiato solo il modello da {string} a {string}',
  async (
    { memory },
    name: string,
    count: number,
    before: number,
    after: number,
    previousModel: string,
    nextModel: string,
  ) => {
    // Every version changes something from the one before; the one the scenario names changes only the model.
    const instructionsOf = (number: number) => `istruzioni della versione ${number}`;
    const changes = Array.from({ length: count }, (_, index) =>
      index + 1 === after
        ? { instructions: instructionsOf(before), model: nextModel }
        : { instructions: instructionsOf(index + 1), model: previousModel },
    );
    memory.described = { name, versions: versionsWith(...changes) };
  },
);

/** The user who owns the flow of the background signs in and reaches its versions from the page of the flow. */
const openVersions = async (dashboard: DashboardPages, memory: ScenarioMemory, account: string) => {
  const flow = memory.described;
  if (flow === undefined) {
    throw new Error('the background describes no flow');
  }
  fakePlatform.addUser(account, { hasUserRole: true });
  fakePlatform.addFlow(account, flow.name, { versions: flow.versions });
  await dashboard.openAndSignInAs(account);
  await dashboard.openVersionsOf(flow.name);
};

When(
  '{string} apre le versioni del flusso {string}',
  async ({ dashboard, memory }, account: string, name: string) => {
    expect(memory.described?.name).toBe(name);
    await openVersions(dashboard, memory, account);
  },
);

When(
  '{string} confronta le versioni {int} e {int}',
  async ({ dashboard, memory }, account: string, first: number, second: number) => {
    await openVersions(dashboard, memory, account);
    memory.compared = [first, second];
    await dashboard.compare(first, second);
  },
);

When(
  '{string} confronta la versione {int} con sé stessa',
  async ({ dashboard, memory }, account: string, version: number) => {
    await openVersions(dashboard, memory, account);
    memory.compared = [version, version];
    await dashboard.compare(version, version);
  },
);

Then(
  'vede le versioni {int}, {int} e {int} con data e ora',
  async ({ dashboard, memory }, newest: number, middle: number, oldest: number) => {
    const numbers = [newest, middle, oldest];
    const items = dashboard.versions().getByRole('listitem');
    await expect(items).toHaveText(numbers.map((number) => new RegExp(`^Versione ${number} · `)));
    const times = items.locator('time');
    await expect(times).toHaveText(numbers.map(() => DATE_AND_TIME));
    const savedAt = new Map(
      memory.described?.versions.map((version) => [version.number, version.createdAt]),
    );
    for (const [index, number] of numbers.entries()) {
      await expect(times.nth(index)).toHaveAttribute('datetime', savedAt.get(number) ?? '');
    }
  },
);

Then(
  'le vede affiancate con evidenziato solo il modello, da {string} a {string}',
  async ({ dashboard, memory, page }, before: string, after: string) => {
    const comparison = dashboard.comparison();
    await expect(comparison.getByRole('columnheader')).toHaveText([
      'Campo',
      ...memory.compared.map((number) => `Versione ${number}`),
    ]);
    const changed = comparison.getByRole('row').filter({ has: page.locator('mark') });
    await expect(changed).toHaveCount(1);
    await expect(changed.getByRole('rowheader')).toHaveText('modello');
    await expect(changed.locator('mark')).toHaveText([before, after]);
  },
);
