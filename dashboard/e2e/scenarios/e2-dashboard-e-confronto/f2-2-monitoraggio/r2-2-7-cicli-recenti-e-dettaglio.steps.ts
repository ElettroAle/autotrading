import { expect } from '@playwright/test';

import {
  aCompletedCycle,
  aFailedCycle,
  apiInstant,
  reasoningOf,
  STEPS,
  type FakeCycle,
} from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The scenario reads times of a day in Italy; the browser of the scenarios runs in the same time zone.
const DAY = '2026-11-14';
const CYCLE_MINUTES = 15;
const MINUTE = 60_000;

const instantAt = (time: string): Date => new Date(`${DAY}T${time}+01:00`);

const cycleAt = (memory: ScenarioMemory, time: string): FakeCycle => {
  const cycle = memory.cycles.find(
    (candidate) => candidate.planned_at === apiInstant(instantAt(time)),
  );
  if (cycle === undefined) {
    throw new Error(`no cycle at ${time}`);
  }
  return cycle;
};

const contentOf = (cycle: FakeCycle, step: string): Record<string, unknown> => {
  const document = cycle.documents.find((candidate) => candidate.step === step);
  if (document === undefined) {
    throw new Error(`the cycle did not get to ${step}`);
  }
  return document.content;
};

const firstMessageOf = (cycle: FakeCycle): string => {
  const [message] = contentOf(cycle, STEPS.composeContext).messaggi as { contenuto: string }[];
  return message?.contenuto ?? '';
};

const openCycleAs = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  time: string,
): Promise<void> => {
  fakePlatform.giveFlowTo(account, memory.flow);
  await dashboard.openCyclesOf(memory.flow);
  await dashboard.signInAs(account);
  await dashboard.page.getByRole('link', { name: time }).click();
  memory.account = account;
};

Given(
  "che il flusso {string} ha {int} cicli, l'ultimo concluso alle {time} con un'apertura long su {string}",
  async ({ memory }, flow: string, count: number, time: string, asset: string) => {
    const last = instantAt(time).getTime();
    memory.flow = flow;
    memory.cycles = Array.from({ length: count }, (_, index) =>
      aCompletedCycle(new Date(last - index * CYCLE_MINUTES * MINUTE), asset),
    );
    fakePlatform.recordCycles(flow, memory.cycles);
  },
);

Given(
  'che il ciclo delle {time} è fallito nel passo della decisione',
  async ({ memory }, time: string) => {
    const completed = cycleAt(memory, time);
    const failed = aFailedCycle(completed, STEPS.agentDecision, {
      errorType: 'ModelCallTimeoutError',
      message: 'il modello non ha risposto entro 60 secondi',
    });
    memory.cycles = memory.cycles.map((cycle) => (cycle === completed ? failed : cycle));
    fakePlatform.recordCycles(memory.flow, memory.cycles);
  },
);

When(
  '{string} apre i cicli del flusso {string}',
  async ({ dashboard }, account: string, flow: string) => {
    fakePlatform.giveFlowTo(account, flow);
    await dashboard.openCyclesOf(flow);
    await dashboard.signInAs(account);
  },
);

When(
  '{string} apre il ciclo delle {time}',
  async ({ dashboard, memory }, account: string, time: string) => {
    await openCycleAs(dashboard, memory, account, time);
  },
);

Then(
  'il primo è quello delle {time} con esito {word} e decisione {string}',
  async ({ dashboard }, time: string, outcome: string, decision: string) => {
    const first = dashboard.cycleRows().first();
    await expect(first).toContainText(time);
    await expect(first).toContainText(outcome);
    await expect(first).toContainText(decision);
  },
);

Then(
  'la pagina mostra {int} cicli con il comando per la pagina successiva',
  async ({ dashboard }, count: number) => {
    await expect(dashboard.cycleRows()).toHaveCount(count);
    await expect(dashboard.nextPage()).toBeVisible();
  },
);

Then(
  'vede ragionamento completo, contesto inviato, risposta integrale, indicatori, previsioni, esito del rischio e ordine su {string}',
  async ({ dashboard, memory }, asset: string) => {
    const cycle = memory.cycles[0] as FakeCycle;
    await expect(dashboard.section('Decisioni e ragionamento')).toContainText(reasoningOf(asset));
    await expect(dashboard.section('Contesto inviato')).toContainText(firstMessageOf(cycle));
    await expect(dashboard.section("Risposta integrale dell'agente")).toContainText(
      String(contentOf(cycle, STEPS.agentDecision).risposta),
    );
    await expect(dashboard.section('Dati delle fonti')).toContainText('indicatori');
    await expect(dashboard.section('Dati delle fonti')).toContainText('forecast');
    await expect(dashboard.section('Controllo del rischio')).toContainText('ApprovedOpening');
    await expect(dashboard.section('Esecuzione degli ordini')).toContainText(`"coin": "${asset}"`);
  },
);

Then(
  "vede il passo fallito, il motivo e ciò che il ciclo ha prodotto prima dell'errore",
  async ({ dashboard, memory }) => {
    const failed = memory.cycles.find((cycle) => cycle.failure !== null) as FakeCycle;
    await expect(dashboard.failure()).toContainText(STEPS.agentDecision);
    await expect(dashboard.failure()).toContainText(failed.failure?.message ?? '');
    await expect(dashboard.section('Contesto inviato')).toContainText(firstMessageOf(failed));
    await expect(dashboard.section('Decisioni e ragionamento')).toHaveCount(0);
  },
);
