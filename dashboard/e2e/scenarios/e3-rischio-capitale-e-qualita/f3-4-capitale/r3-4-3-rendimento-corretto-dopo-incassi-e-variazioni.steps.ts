import { expect } from '@playwright/test';

import { aCashOut } from '@/testing/mocks/capital-changes';
import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';
import { onFlowPage } from '../../../support/flow-page';

// R3.4.3, ADR rendimento-composto-tra-le-variazioni-di-capitale: the change marked on the equity curve; the other
// scenarios run on the use cases with pytest-bdd.
const HOUR = 60 * 60_000;

Given(
  'che {string} ha il flusso {string} avviato con capitale allocato {int} USDC',
  async ({ memory }, account: string, flow: string, capital: number) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, { allocatedCapital: capital, currentCapital: capital });
    // The first cycle runs when the flow starts: its equity opens the curve.
    fakePlatform.recordEquity(flow, new Date(Date.now() - 3 * HOUR), capital);
    memory.flow = flow;
  },
);

Given(
  'che {string} ha incassato {int} USDC da {string}',
  async ({ memory }, account: string, amount: number, flowName: string) => {
    const flow = fakePlatform.user(account).flows.find((candidate) => candidate.name === flowName);
    if (flow === undefined) {
      throw new Error(`no flow ${flowName} for ${account}`);
    }
    const capital = flow.allocatedCapital ?? 0;
    fakePlatform.recordEquity(flowName, new Date(Date.now() - 2 * HOUR), capital + amount);
    const cashOut = aCashOut(flow, amount, new Date(Date.now() - 1.5 * HOUR));
    fakePlatform.recordCapitalChange(cashOut);
    memory.capitalChangedAt = cashOut.changed_at;
    fakePlatform.recordEquity(flowName, new Date(Date.now() - HOUR), capital);
  },
);

When(
  "{string} apre l'equity curve di {string}",
  async ({ dashboard, memory }, account: string, flow: string) => {
    await onFlowPage(dashboard, memory, account, flow);
    await expect(dashboard.equityCurve()).toBeVisible();
  },
);

Then(
  "la curva segna sull'istante dell'incasso {string}",
  async ({ dashboard, memory }, label: string) => {
    const mark = dashboard.equityCurve().getByRole('link', { name: label, exact: true });
    await expect(mark).toHaveAttribute('data-instant', memory.capitalChangedAt);
  },
);
