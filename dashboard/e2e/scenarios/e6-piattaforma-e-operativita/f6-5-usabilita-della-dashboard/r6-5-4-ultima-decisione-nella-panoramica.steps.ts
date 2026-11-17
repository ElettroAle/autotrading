import { expect, type Locator } from '@playwright/test';

import { paths } from '@/config/paths';
import {
  aCompletedCycle,
  aFailedCycle,
  apiInstant,
  STEPS,
  withDecisions,
  type FakeCycle,
} from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// R6.5.4 on the Panoramica of the flow; pytest-bdd runs the same scenarios on the use cases (ADR
// decisioni-del-ciclo-registrate-per-asset, ADR riquadro-dell-ultima-decisione-nella-panoramica).

// The user who owns the flows of the scenarios and opens their Panoramica.
const OWNER = 'anna';
const SHORTENED_LENGTH = 160;
const REASONING =
  'Il prezzo ha rotto la resistenza con volumi in aumento e il sentiment resta positivo: apro una posizione long ' +
  'con leva contenuta e uno stop sotto il minimo della giornata, pronto a chiuderla se il volume cala.';

/** Today at the time of the scenario, in the time zone of the browser. */
const todayAt = (time: string): Date => {
  const [hours, minutes] = time.split(':').map(Number);
  const instant = new Date();
  instant.setHours(hours ?? 0, minutes ?? 0, 0, 0);
  return instant;
};

const decidedAt = (time: string, asset: string, direction: string, confidence: number): FakeCycle =>
  withDecisions(aCompletedCycle(todayAt(time)), [
    { asset, action: 'apri', reasoning: REASONING, confidence, opening: { direction } },
  ]);

const recordCycles = (flow: string, cycles: FakeCycle[]): void => {
  fakePlatform.giveFlowTo(OWNER, flow);
  fakePlatform.recordCycles(flow, cycles);
};

const panel = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByRole('region', { name: 'Ultima decisione' });

const valueOf = (decision: Locator, label: string): Locator =>
  decision.getByLabel(label, { exact: true });

const cycleLink = (dashboard: DashboardPages, time: string): Locator =>
  panel(dashboard).getByRole('link', { name: new RegExp(`${time}:00$`) });

Given(
  /^che l'ultimo ciclo concluso di "([^"]+)", alle (\d\d:\d\d), ha deciso per (\w+) "apri (long|short)" con confidenza (\d+)$/,
  async (
    { memory },
    flow: string,
    time: string,
    asset: string,
    direction: string,
    confidence: number,
  ) => {
    const earlier = withDecisions(aCompletedCycle(todayAt('09:00')), [
      { asset, action: 'mantieni', reasoning: 'attesa', confidence: 40, opening: null },
    ]);
    recordCycles(flow, [earlier, decidedAt(time, asset, direction, confidence)]);
    memory.flow = flow;
  },
);

Given(
  'che il ciclo delle {word} di {string} è fallito prima della decisione',
  async ({ memory }, time: string, flow: string) => {
    // The cycle at 11:00 fails after the one at 10:00 decided, as the scenario says with «ancora».
    const failed = aFailedCycle(aCompletedCycle(todayAt(time)), STEPS.agentDecision, {
      errorType: 'ModelUnavailableError',
      message: 'fornitore IA non raggiungibile',
    });
    recordCycles(flow, [decidedAt('10:00', 'BTC', 'long', 72), failed]);
    memory.flow = flow;
  },
);

Given('che il flusso {string} non ha cicli conclusi', async ({ memory }, flow: string) => {
  // A cycle failed after the agent decided is not a completed cycle: its decision is not the last decision.
  const failed = aFailedCycle(decidedAt('10:00', 'BTC', 'long', 72), STEPS.riskCheck, {
    errorType: 'ExchangeUnavailableError',
    message: 'exchange non raggiungibile',
  });
  recordCycles(flow, [failed]);
  memory.flow = flow;
});

When(
  '{string} apre la Panoramica del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    memory.flow = flow;
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

Then(
  /^vede l'ultima decisione delle (\d\d:\d\d) con (\w+), "([^"]+)", "([^"]+)", confidenza (\d+) e il ragionamento accorciato$/,
  async (
    { dashboard },
    time: string,
    asset: string,
    action: string,
    direction: string,
    confidence: number,
  ) => {
    await expect(panel(dashboard)).toContainText('indipendente dal periodo');
    await expect(cycleLink(dashboard, time)).toBeVisible();
    const decision = panel(dashboard).getByRole('region', { name: asset, exact: true });
    await expect(decision).toHaveCount(1);
    await expect(valueOf(decision, 'Asset')).toHaveText(asset);
    await expect(valueOf(decision, 'Azione')).toHaveText(action);
    await expect(valueOf(decision, 'Direzione')).toHaveText(direction);
    await expect(valueOf(decision, 'Confidenza')).toHaveText(String(confidence));
    const reasoning = (await valueOf(decision, 'Ragionamento').textContent()) ?? '';
    expect(reasoning.endsWith('…')).toBe(true);
    expect(reasoning.length).toBeLessThanOrEqual(SHORTENED_LENGTH + 1);
    expect(REASONING.startsWith(reasoning.slice(0, -1))).toBe(true);
  },
);

Then(
  'un collegamento al dettaglio del ciclo delle {word}',
  async ({ dashboard, memory }, time: string) => {
    const flowId = fakePlatform.flowNamed(memory.flow).id;
    const href = paths.cycle.getHref(flowId, apiInstant(todayAt(time)));
    expect((await cycleLink(dashboard, time).getAttribute('href'))?.endsWith(href)).toBe(true);
    await cycleLink(dashboard, time).click();
    await dashboard.page.waitForURL((url) => url.pathname.endsWith(href));
  },
);

Then('vede ancora la decisione del ciclo delle {word}', async ({ dashboard }, time: string) => {
  await expect(cycleLink(dashboard, time)).toBeVisible();
  await expect(panel(dashboard).getByRole('link')).toHaveCount(1);
});

Then('il riquadro dice {string}', async ({ dashboard }, text: string) => {
  await expect(panel(dashboard)).toContainText(text);
  await expect(panel(dashboard).getByRole('link')).toHaveCount(0);
});
