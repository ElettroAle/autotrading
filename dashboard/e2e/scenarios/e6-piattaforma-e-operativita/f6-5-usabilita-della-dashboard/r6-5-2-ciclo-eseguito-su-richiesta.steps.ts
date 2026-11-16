import { expect } from '@playwright/test';

import { aCompletedCycle, STEPS } from '@/testing/mocks/cycles';
import { accessTokenOf, fakePlatform, flowIdOf } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

// R6.5.2, ADR pulsante-esegui-ora-nella-pagina-del-flusso: the dashboard asks the fake API for the cycle; the worker
// that runs it is pytest-bdd's, on the use cases.
const RUN_NOW = 'Esegui ora';
// The day of the scenario, read in the time zone of the browser of the scenarios.
const DAY = '2026-11-16';
const instantAt = (time: string): Date => new Date(`${DAY}T${time}:00+01:00`);
const RUNNING_CYCLES = /\/flows\/[^/]+\/cycles$/;

const answerOfRunNow = (dashboard: DashboardPages) =>
  dashboard.page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      RUNNING_CYCLES.test(new URL(response.url()).pathname),
  );

const cyclesAskedFor = (flow: string) =>
  fakePlatform.cyclesOf(flowIdOf(flow)).filter((cycle) => cycle.trigger === 'on_demand');

Given(
  'che {string} ha il flusso attivo {string} con un ciclo ogni {int} minuti, il prossimo alle {word}',
  async ({ memory }, account: string, flow: string, minutes: number, next: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow).cycleMinutes = minutes;
    const lastPlanned = new Date(instantAt(next).getTime() - minutes * 60_000);
    fakePlatform.recordCycles(flow, [aCompletedCycle(lastPlanned)]);
    memory.flow = flow;
  },
);

Given('che un ciclo di {string} è in corso', async ({}, flow: string) => {
  fakePlatform.holdCycle(flow);
});

Given('che il flusso {string} è in pausa', async ({}, flow: string) => {
  fakePlatform.changeFlow(flow, { status: 'in pausa' });
});

Given('che il flusso {string} è fermo', async ({}, flow: string) => {
  fakePlatform.changeFlow(flow, { status: 'fermo' });
});

When(
  '{string} sceglie «Esegui ora» sul flusso {string} alle {word}',
  async ({ dashboard, memory }, account: string, flow: string, time: string) => {
    fakePlatform.setWorkerClock(instantAt(time));
    memory.newCycleAt = time;
    await onFlowPage(dashboard, memory, account, flow);
    await dashboard.flowCommand(RUN_NOW).click();
  },
);

When(
  '{string} sceglie «Esegui ora» sul flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    const answer = answerOfRunNow(dashboard);
    await dashboard.flowCommand(RUN_NOW).click();
    memory.answerStatus = (await answer).status();
  },
);

Then('il worker esegue un ciclo completo di {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.message('Ciclo eseguito: concluso.')).toBeVisible();
  expect(cyclesAskedFor(flow).map((cycle) => cycle.steps)).toEqual([Object.values(STEPS)]);
});

Then('il ciclo compare tra i cicli come eseguito su richiesta', async ({ dashboard, memory }) => {
  await dashboard.flowTab('Cicli').click();
  await expect(dashboard.cycles()).toContainText(`${memory.newCycleAt}:00 · su richiesta`);
});

Then(
  'il ciclo pianificato successivo resta alle {word}',
  async ({ dashboard, memory }, next: string) => {
    await dashboard.open();
    await expect(dashboard.flowFact(memory.flow, 'Prossima esecuzione prevista')).toContainText(
      `${next}:00`,
    );
  },
);

Then(
  'la richiesta è rifiutata con stato {int} e il motivo {string}',
  async ({ dashboard, memory }, status: number, reason: string) => {
    expect(memory.answerStatus).toBe(status);
    await expect(dashboard.message(`Ciclo rifiutato: ${reason}`)).toBeVisible();
  },
);

Then('non parte un secondo ciclo', async ({ memory }) => {
  expect(cyclesAskedFor(memory.flow)).toEqual([]);
});

Then('non vede il comando «Esegui ora»', async ({ dashboard }) => {
  await expect(dashboard.flowStatus()).toBeVisible();
  await expect(dashboard.flowCommand(RUN_NOW)).toHaveCount(0);
});

Then(
  "la richiesta dall'interfaccia programmatica è rifiutata con il motivo {string}",
  async ({ dashboard, memory }, reason: string) => {
    const answer = await dashboard.page.evaluate(
      async (request) => {
        const response = await fetch(request.path, {
          method: 'POST',
          headers: { Authorization: `Bearer ${request.token}` },
        });
        return { status: response.status, body: (await response.json()) as { detail?: string } };
      },
      { token: accessTokenOf(memory.account), path: `/flows/${flowIdOf(memory.flow)}/cycles` },
    );
    expect([answer.status, answer.body.detail]).toEqual([409, reason]);
  },
);
