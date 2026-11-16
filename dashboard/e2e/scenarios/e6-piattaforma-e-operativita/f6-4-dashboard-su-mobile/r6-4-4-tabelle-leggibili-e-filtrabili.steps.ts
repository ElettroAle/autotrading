import { expect, type Locator } from '@playwright/test';

import { paths } from '@/config/paths';
import { aCompletedCycle, aFailedCycle, STEPS, type FakeCycle } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from '../../../support/dashboard-pages';
import {
  measurePages,
  preparePagesWithLongWords,
  signInOnTheFlows,
} from '../../../support/every-page';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The flow of the scenarios that name none.
const THE_FLOW = 'alfa';
const SCREEN_HEIGHT = 800;
const LAST = Date.UTC(2026, 10, 14, 9, 0);
const QUARTER = 15 * 60_000;
const HOUR = 3_600_000;

const instantBack = (steps: number): Date => new Date(LAST - steps * QUARTER);

const aFailedCycleAt = (steps: number): FakeCycle =>
  aFailedCycle(aCompletedCycle(instantBack(steps)), STEPS.agentDecision, {
    errorType: 'ModelCallTimeoutError',
    message: 'il modello non ha risposto',
  });

const recordCycles = (memory: ScenarioMemory, flow: string, cycles: FakeCycle[]): void => {
  memory.flow = flow;
  memory.cycles = cycles;
  fakePlatform.recordCycles(flow, cycles);
};

/** Completed cycles, each with an opening, then failed ones that never got to a decision, newest first. */
const completedThenFailed = (completed: number, failed: number): FakeCycle[] => [
  ...Array.from({ length: completed }, (_, index) => aCompletedCycle(instantBack(index))),
  ...Array.from({ length: failed }, (_, index) => aFailedCycleAt(completed + index)),
];

/** Opens a page of the flow of the scenario as the user: the first page asks to sign in and brings back to it. */
const openAs = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  open: () => Promise<void>,
): Promise<void> => {
  fakePlatform.giveFlowTo(account, memory.flow || THE_FLOW);
  await open();
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.signInAs(account);
  }
};

const choice = (dashboard: DashboardPages, name: string): Locator =>
  dashboard.page.getByRole('button', { name, exact: true });

const count = (dashboard: DashboardPages, text: string): Locator =>
  dashboard.content().getByText(text, { exact: true });

const filterCycles = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  option: string,
): Promise<void> => {
  await openAs(dashboard, memory, account, () => dashboard.openCyclesOf(memory.flow));
  await expect(count(dashboard, `${memory.cycles.length} cicli`)).toBeVisible();
  await choice(dashboard, option).click();
  await expect(choice(dashboard, option)).toHaveAttribute('aria-pressed', 'true');
};

const filterClosedPositions = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  option: string,
): Promise<void> => {
  await openAs(dashboard, memory, account, () => dashboard.openClosedPositionsOf(memory.flow));
  await expect(dashboard.closedPositionRows().first()).toBeVisible();
  await choice(dashboard, option).click();
  await expect(choice(dashboard, option)).toHaveAttribute('aria-pressed', 'true');
};

Given(
  'che il flusso {string} ha {int} cicli conclusi e {int} falliti',
  ({ memory }, flow: string, completed: number, failed: number) => {
    recordCycles(memory, flow, completedThenFailed(completed, failed));
  },
);

When(
  '{string} filtra i cicli del flusso sui falliti',
  async ({ dashboard, memory }, account: string) => {
    await filterCycles(dashboard, memory, account, 'Falliti');
  },
);

Then(
  'vede {int} cicli, tutti falliti, e il conteggio {string}',
  async ({ dashboard }, cycles: number, text: string) => {
    await expect(dashboard.cycleRows()).toHaveCount(cycles);
    for (const row of await dashboard.cycleRows().all()) {
      await expect(dashboard.cell(row, 'Esito')).toContainText('fallito');
    }
    await expect(count(dashboard, text)).toBeVisible();
  },
);

Given(
  "che il flusso {string} ha {int} cicli con un'apertura",
  ({ memory }, flow: string, openings: number) => {
    // Two cycles without any decision, which the filter leaves out.
    recordCycles(memory, flow, completedThenFailed(openings, 2));
  },
);

When(
  '{string} filtra i cicli del flusso sulle aperture',
  async ({ dashboard, memory }, account: string) => {
    await filterCycles(dashboard, memory, account, 'Aperture');
  },
);

Then("vede {int} cicli, tutti con un'apertura", async ({ dashboard }, cycles: number) => {
  await expect(dashboard.cycleRows()).toHaveCount(cycles);
  for (const row of await dashboard.cycleRows().all()) {
    await expect(dashboard.cell(row, 'Decisioni')).toContainText('apri');
  }
});

Given(
  'che il flusso {string} ha {int} posizioni chiuse short vinte e {int} long persa',
  ({ memory }, flow: string, won: number, lost: number) => {
    memory.flow = flow;
    fakePlatform.recordClosedPositions(flow, [
      ...Array.from({ length: won }, (_, index) =>
        aClosedPosition({ closedAt: new Date(LAST - index * HOUR), side: 'short', pnl: '3' }),
      ),
      ...Array.from({ length: lost }, (_, index) =>
        aClosedPosition({ closedAt: new Date(LAST - (won + index) * HOUR), pnl: '-2' }),
      ),
    ]);
  },
);

When(
  '{string} filtra le posizioni chiuse sulle perse',
  async ({ dashboard, memory }, account: string) => {
    await filterClosedPositions(dashboard, memory, account, 'Perse');
  },
);

Then('vede solo la posizione long persa', async ({ dashboard }) => {
  await expect(dashboard.closedPositionRows()).toHaveCount(1);
  const row = dashboard.closedPositionRows().first();
  await expect(dashboard.cell(row, 'Direzione')).toHaveText(/long$/);
  await expect(dashboard.cell(row, 'PnL')).toContainText('-2');
});

Given(
  'che {string} ha filtrato i cicli sui falliti',
  async ({ dashboard, memory }, account: string) => {
    recordCycles(memory, THE_FLOW, completedThenFailed(5, 2));
    await filterCycles(dashboard, memory, account, 'Falliti');
    await expect(dashboard.cycleRows()).toHaveCount(2);
  },
);

When('azzera i filtri', async ({ dashboard }) => {
  await dashboard.button('Azzera i filtri').click();
});

Then('vede tutti i cicli del periodo', async ({ dashboard, memory }) => {
  await expect(dashboard.cycleRows()).toHaveCount(memory.cycles.length);
  await expect(count(dashboard, `${memory.cycles.length} cicli`)).toBeVisible();
  await expect(choice(dashboard, 'Tutti')).toHaveAttribute('aria-pressed', 'true');
});

When(
  '{string} sceglie un punto qualsiasi della riga di un ciclo',
  async ({ dashboard, memory }, account: string) => {
    recordCycles(memory, THE_FLOW, completedThenFailed(1, 1));
    await openAs(dashboard, memory, account, () => dashboard.openCyclesOf(memory.flow));
    // The outcome, away from the instant that links the cycle: the row itself opens it.
    await dashboard.cell(dashboard.cycleRows().nth(1), 'Esito').click();
  },
);

Then('vede il dettaglio di quel ciclo', async ({ dashboard, memory }) => {
  const chosen = memory.cycles[1] as FakeCycle;
  const flowId = fakePlatform.flowNamed(memory.flow).id;
  await expect(dashboard.page).toHaveURL(
    (url) => url.pathname === `/dashboard${paths.cycle.getHref(flowId, chosen.planned_at)}`,
  );
  await expect(dashboard.pageHeading()).toHaveText('Dettaglio del ciclo');
  await expect(dashboard.failure()).toContainText(chosen.failure?.message ?? '');
});

Given(
  'uno schermo largo {int} pixel e uno largo {int} pixel',
  ({ memory }, narrow: number, wide: number) => {
    memory.screenWidths = [narrow, wide];
  },
);

When(
  '{string} apre posizioni chiuse, cicli e classifica dei flussi',
  async ({ dashboard, memory }, account: string) => {
    // Many columns and long words: the widest the tables of the dashboard get.
    const pages = preparePagesWithLongWords(account, THE_FLOW);
    memory.account = account;
    await signInOnTheFlows(dashboard, account);
    const tables = {
      'posizioni chiuse': pages.flowClosedPositions,
      cicli: pages.flowCycles,
      classifica: pages.ranking,
    };
    for (const width of memory.screenWidths) {
      await dashboard.page.setViewportSize({ width, height: SCREEN_HEIGHT });
      const measured = await measurePages(dashboard, tables);
      measured.forEach((spilled, page) => memory.spilledByPage.set(`${page} a ${width}`, spilled));
    }
  },
);

Then('nessuna pagina scorre in orizzontale', ({ memory }) => {
  expect(memory.spilledByPage.size).toBe(3 * memory.screenWidths.length);
  expect(
    Object.fromEntries([...memory.spilledByPage].filter(([, spilled]) => spilled.length > 0)),
  ).toEqual({});
});

Given(
  'che {string} ha filtrato le posizioni chiuse sulle short',
  async ({ dashboard, memory }, account: string) => {
    memory.flow = THE_FLOW;
    fakePlatform.giveFlowTo(account, THE_FLOW);
    fakePlatform.recordClosedPositions(THE_FLOW, [
      aClosedPosition({ closedAt: new Date(LAST), side: 'short' }),
      aClosedPosition({ closedAt: new Date(LAST - HOUR), side: 'long' }),
    ]);
    await filterClosedPositions(dashboard, memory, account, 'Short');
    await expect(dashboard.closedPositionRows()).toHaveCount(1);
  },
);

When('ricarica la pagina', async ({ dashboard }) => {
  await dashboard.page.reload();
});

Then('il filtro sulle short è ancora attivo', async ({ dashboard }) => {
  await expect(choice(dashboard, 'Short')).toHaveAttribute('aria-pressed', 'true');
  await expect(dashboard.closedPositionRows()).toHaveCount(1);
  await expect(dashboard.cell(dashboard.closedPositionRows().first(), 'Direzione')).toHaveText(
    /short$/,
  );
});
