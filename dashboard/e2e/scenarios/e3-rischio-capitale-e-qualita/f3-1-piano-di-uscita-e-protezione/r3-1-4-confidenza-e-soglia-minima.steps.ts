import { expect } from '@playwright/test';

import { aCompletedCycle } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// The cycle of the decision, at a time of a day in Italy, as the browser of the scenarios reads it.
const DECISION_TIME = '10:07:00';
const DECIDED_AT = new Date(`2026-11-14T${DECISION_TIME}+01:00`);

Given(
  'che {string} ha il flusso {string} attivo con asset {string} e confidenza minima {int}',
  async ({ memory }, account: string, flow: string, asset: string, minimum: number) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, { assets: [asset], minimumConfidence: minimum });
    memory.account = account;
    memory.flow = flow;
  },
);

// The worker recorded the decision with its confidence in the cycle; the dashboard only reads it (R3.1.4).
Given(
  "che l'agente di {string} ha deciso di aprire long su {string} con confidenza {int}",
  async ({ memory }, flow: string, asset: string, confidence: number) => {
    memory.flow = flow;
    memory.cycles = [aCompletedCycle(DECIDED_AT, asset, undefined, confidence)];
    fakePlatform.recordCycles(flow, memory.cycles);
  },
);

When(
  '{string} apre nella dashboard il dettaglio di quel ciclo',
  async ({ dashboard, memory }, account: string) => {
    await dashboard.openCyclesOf(memory.flow);
    await dashboard.signInAs(account);
    await dashboard.page.getByRole('link', { name: DECISION_TIME }).click();
  },
);

Then(
  'la decisione su {string} mostra confidenza {int}',
  async ({ dashboard }, asset: string, confidence: number) => {
    const details = dashboard.page.getByRole('group', { name: `Decisione su ${asset}` });
    await expect(details).toContainText(`Confidenza${confidence}`);
  },
);
