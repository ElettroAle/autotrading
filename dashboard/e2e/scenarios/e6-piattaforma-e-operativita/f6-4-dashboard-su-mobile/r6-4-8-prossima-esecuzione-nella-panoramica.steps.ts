import { expect } from '@playwright/test';

import { aCompletedCycle } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// R6.4.8, ADR prossima-esecuzione-nel-riepilogo-del-flusso and nomi-e-istanti-dei-guadagni: the overview of the page of
// the flow says when the next cycle falls, the instant the API plans; the period of the page does not move it.
// The day of the scenario, read in the time zone of the browser of the scenarios.
const DAY = '2026-11-18';
const SHOWN_DAY = '18/11/2026';
const instantAt = (time: string): Date => new Date(`${DAY}T${time}:00+01:00`);

Given(
  'che {string} ha il flusso {string} con un ciclo ogni {int} minuti',
  async ({ memory }, account: string, flow: string, minutes: number) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow).cycleMinutes = minutes;
    memory.flow = flow;
  },
);

Given(
  "che il flusso {string} è attivo e l'ultimo ciclo è partito alle {word}",
  async ({}, flow: string, time: string) => {
    fakePlatform.changeFlow(flow, { status: 'attivo' });
    fakePlatform.recordCycles(flow, [aCompletedCycle(instantAt(time))]);
  },
);

When(
  '{string} apre la panoramica del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    memory.account = account;
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowTab('Panoramica')).toHaveAttribute('aria-current', 'page');
  },
);

Then('vede {string} alle {word}', async ({ dashboard }, term: string, time: string) => {
  await expect(dashboard.result(term)).toContainText(`${SHOWN_DAY}, ${time}`);
});

Then('vede {string}', async ({ dashboard }, term: string) => {
  await expect(dashboard.result(term)).toBeVisible();
});

Then('non vede {string}', async ({ dashboard }, term: string) => {
  await expect(dashboard.result('Guadagno attuale')).toBeVisible();
  await expect(dashboard.result(term)).toHaveCount(0);
});

// Bug 690, ADR pagina-del-flusso-archiviato-in-sola-lettura: the page of an archived flow opens in read only, from its
// address, with its status, no next cycle and no command.
Given('che il flusso {string} è archiviato', async ({}, flow: string) => {
  fakePlatform.changeFlow(flow, { status: 'archiviato' });
});

Then(
  'il flusso {string} mostra lo stato {string}',
  async ({ dashboard }, flow: string, status: string) => {
    await expect(dashboard.page.getByRole('region', { name: flow, exact: true })).toContainText(
      `Stato: ${status}`,
    );
  },
);

Then('vede {string} con {string}', async ({ dashboard }, term: string, value: string) => {
  await expect(dashboard.result(term)).toHaveText(value);
});

Then('non vede alcun comando del flusso', async ({ dashboard, memory }) => {
  const head = dashboard.page.getByRole('region', { name: memory.flow, exact: true });
  await expect(head).toBeVisible();
  await expect(head.getByRole('button')).toHaveCount(0);
  await expect(head.getByRole('link')).toHaveCount(0);
});
