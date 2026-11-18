import { expect, type Locator } from '@playwright/test';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then } from '../../../support/fixtures';
import { HOUR, MINUTE, minutesAgo, pointAt, recordFlow } from '../../../support/period-history';

// R6.4.6, ADR periodi-brevi-come-durata-nel-dominio and periodi-brevi-nel-selettore-condiviso: the steps it shares with
// R6.4.7 are in e2e/support/period-menu.steps.ts.
const equitySection = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByRole('region', { name: 'Equity curve' });

const mentioning = (text: string): RegExp =>
  new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');

Given(
  "che il flusso {string} ha un ciclo ogni {int} minuti e l'ultimo {int} minuti fa",
  async ({ memory }, flow: string, every: number, ago: number) => {
    recordFlow(memory.owner, flow, minutesAgo(ago).getTime(), every * MINUTE);
  },
);

Given(
  "che l'ultimo ciclo del flusso {string} è di {int} minuti fa",
  async ({ memory }, flow: string, ago: number) => {
    recordFlow(memory.owner, flow, minutesAgo(ago).getTime(), HOUR);
  },
);

Then(
  "l'equity curve mostra il solo punto del ciclo di {int} minuti fa",
  async ({ dashboard }, ago: number) => {
    await expect(dashboard.equityPoints()).toHaveCount(1);
    await expect(pointAt(dashboard, minutesAgo(ago))).toBeVisible();
  },
);

Then("l'equity curve dice {string}", async ({ dashboard }, text: string) => {
  await expect(equitySection(dashboard)).toContainText(mentioning(text));
  await expect(dashboard.equityCurve()).toHaveCount(0);
});

Then('le statistiche dicono {string}', async ({ dashboard }, text: string) => {
  await expect(dashboard.statistics()).toContainText(mentioning(text));
});
