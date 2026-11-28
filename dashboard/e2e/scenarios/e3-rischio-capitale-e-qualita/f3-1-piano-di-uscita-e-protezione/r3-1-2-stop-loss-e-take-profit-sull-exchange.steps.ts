import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The reconciliation interval of the account on its page, with its info button (Bug 778, ADR
// intervallo-di-riconciliazione-del-conto): the API checks the range, the dashboard sends what the user types.

const FIELD = 'Intervallo di riconciliazione (minuti)';

const section = (dashboard: DashboardPages, memory: ScenarioMemory): Locator =>
  dashboard.content().getByRole('region', {
    name: `Riconciliazione periodica del conto ${memory.subject}`,
  });

When(
  /^imposta l'intervallo di riconciliazione a (\d+) minuti e salva$/,
  async ({ dashboard, memory }, minutes: number) => {
    // The page open is the one of the only account of the user.
    memory.subject = fakePlatform.user(memory.account).accounts[0]?.name ?? '';
    const interval = section(dashboard, memory);
    await interval.getByLabel(FIELD, { exact: true }).fill(String(minutes));
    await interval.getByRole('button', { name: "Salva l'intervallo", exact: true }).click();
  },
);

Then(
  /^la pagina mostra l'intervallo di riconciliazione di (\d+) minuti$/,
  async ({ dashboard, memory }, minutes: number) => {
    const interval = section(dashboard, memory);
    await expect(interval.getByRole('status')).toHaveText(
      `Intervallo di riconciliazione: ${minutes} minuti`,
    );
    await expect(interval.getByLabel(FIELD, { exact: true })).toHaveValue(String(minutes));
    expect(fakePlatform.accountNamed(memory.subject).reconciliationIntervalMinutes).toBe(minutes);
  },
);

Then('il campo ha il pulsante {string}', async ({ dashboard, memory }, button: string) => {
  await expect(
    section(dashboard, memory).getByRole('button', { name: button, exact: true }),
  ).toBeVisible();
});
