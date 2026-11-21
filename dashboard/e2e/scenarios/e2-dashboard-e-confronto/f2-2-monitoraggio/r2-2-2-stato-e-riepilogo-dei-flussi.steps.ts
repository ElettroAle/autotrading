import { expect } from '@playwright/test';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then } from '../../../support/fixtures';

// The scenario reads times of a day in Italy; the browser of the scenarios runs in the same time zone.
const LAST_CYCLE = new Date('2026-11-14T10:07:00+01:00');
const LAST_CYCLE_TIME = '10:07:00';
const NEXT_CYCLE_TIME = '10:22:00';
const CYCLE_MINUTES = 15;
const MINUTE = 60_000;
const RECORDED_CYCLES = 12;

const cyclesUntilLast = () =>
  Array.from({ length: RECORDED_CYCLES }, (_, index) => {
    const cycle = aCompletedCycle(new Date(LAST_CYCLE.getTime() - index * CYCLE_MINUTES * MINUTE));
    return index === 1
      ? aFailedCycle(cycle, STEPS.agentDecision, {
          errorType: 'ModelCallTimeoutError',
          message: 'il modello non ha risposto entro 60 secondi',
        })
      : cycle;
  });

Given(
  'che {string} ha il flusso {string} attivo sul conto {string} con capitale iniziale {int} USDC e capitale attuale {int} USDC',
  async (
    { memory },
    account: string,
    flow: string,
    accountName: string,
    initial: number,
    current: number,
  ) => {
    fakePlatform.giveFlowTo(account, flow);
    fakePlatform.changeFlow(flow, {
      status: 'attivo',
      accountId: fakePlatform.addAccount(account, accountName).id,
      allocatedCapital: initial,
      currentCapital: current,
    });
    fakePlatform.recordCycles(flow, cyclesUntilLast());
    memory.account = account;
  },
);

Given(
  'che il flusso {string} è in pausa automatica per {string}',
  async ({ memory }, flow: string, reason: string) => {
    fakePlatform.giveFlowTo(memory.account, flow);
    fakePlatform.changeFlow(flow, { status: 'in pausa', pauseReason: reason });
  },
);

Given(
  'che il flusso {string} ha capitale attuale {int} USDC',
  async ({}, flow: string, current: number) => {
    fakePlatform.changeFlow(flow, { currentCapital: current });
  },
);

Then(
  'il flusso {string} mostra stato {string}, capitale iniziale {int} USDC, capitale attuale {int} USDC e rendimento {word} in verde',
  async (
    { dashboard, memory },
    flow: string,
    status: string,
    initial: number,
    current: number,
    flowReturn: string,
  ) => {
    memory.flow = flow;
    await expect(dashboard.flowFact(flow, 'Stato')).toHaveText(status);
    await expect(dashboard.flowFact(flow, 'Capitale iniziale')).toHaveText(`${initial} USDC`);
    await expect(dashboard.flowFact(flow, 'Capitale attuale')).toHaveText(`${current} USDC`);
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveText(flowReturn);
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveClass(/text-green-/);
  },
);

Then('mostra ultima esecuzione e prossima esecuzione prevista', async ({ dashboard, memory }) => {
  await expect(dashboard.flowFact(memory.flow, 'Ultima esecuzione')).toContainText(
    `${LAST_CYCLE_TIME} · concluso`,
  );
  await expect(dashboard.flowFact(memory.flow, 'Prossima esecuzione prevista')).toContainText(
    NEXT_CYCLE_TIME,
  );
});

Then(
  'il flusso {string} mostra stato {string} con il motivo {string}',
  async ({ dashboard, memory }, flow: string, status: string, reason: string) => {
    memory.flow = flow;
    await expect(dashboard.flowFact(flow, 'Stato')).toHaveText(status);
    await expect(dashboard.flowFact(flow, 'Motivo della pausa')).toHaveText(reason);
  },
);

Then('non mostra una prossima esecuzione prevista', async ({ dashboard, memory }) => {
  await expect(dashboard.flowFact(memory.flow, 'Stato')).toBeVisible();
  await expect(dashboard.flowFact(memory.flow, 'Prossima esecuzione prevista')).toHaveCount(0);
});

Then(
  'il flusso {string} mostra rendimento {word} in rosso',
  async ({ dashboard }, flow: string, flowReturn: string) => {
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveText(flowReturn);
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveClass(/text-red-/);
  },
);

Then(
  'il flusso {string} mostra conto {string}, modello {string} e ultima esecuzione {string}',
  async ({ dashboard }, flow: string, account: string, model: string, outcome: string) => {
    await expect(dashboard.flowFact(flow, 'Conto')).toHaveText(account);
    await expect(dashboard.flowFact(flow, 'Modello')).toHaveText(model);
    await expect(dashboard.flowFact(flow, 'Ultima esecuzione')).toContainText(
      `${LAST_CYCLE_TIME} · ${outcome}`,
    );
  },
);

// Even is neither a gain nor a loss: grey, as in every view that colours a result (Bug 620).
Then(
  'il flusso {string} mostra rendimento {word} in grigio',
  async ({ dashboard }, flow: string, flowReturn: string) => {
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveText(flowReturn);
    await expect(dashboard.flowFact(flow, 'Rendimento')).toHaveClass(/text-slate-/);
  },
);
