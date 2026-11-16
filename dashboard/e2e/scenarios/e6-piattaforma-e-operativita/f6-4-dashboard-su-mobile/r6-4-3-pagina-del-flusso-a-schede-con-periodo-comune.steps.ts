import { expect, type Locator } from '@playwright/test';

import { aCompletedCycle, aFailedCycle, apiInstant, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition, anOpenPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, intervallo-trascinando-sull-equity-curve and
// cicli-falliti-sull-equity-curve.
const DAY = 24 * 60 * 60_000;
const HISTORY_DAYS = 30;
const INITIAL_CAPITAL = 1000;
const CYCLE_HOUR = 10;
const CYCLE_MINUTE = 15;
const CLOSING_HOUR = 12;
// The days the scenarios name, in November 2026, are part of the history whatever day the scenarios run on.
const NAMED_DAYS = Array.from({ length: 11 }, (_, index) => 5 + index);
const NOVEMBER = 10;
const YEAR = 2026;
const PERIODS: Readonly<Record<string, string>> = { 'ultima settimana': '7 giorni' };
const FLOW_TABS = 'Dati del flusso';
const REMOVE_INTERVAL = "Togli l'intervallo";

const cycleOfDay = (year: number, month: number, day: number): Date =>
  new Date(year, month, day, CYCLE_HOUR, CYCLE_MINUTE);

const novemberDay = (day: number): string => `${YEAR}-11-${String(day).padStart(2, '0')}`;

const daysOfHistory = (): Date[] => {
  const now = new Date();
  const recent = Array.from({ length: HISTORY_DAYS }, (_, index) => {
    const day = new Date(now.getTime() - index * DAY);
    return cycleOfDay(day.getFullYear(), day.getMonth(), day.getDate());
  }).filter((instant) => instant.getTime() <= now.getTime());
  const named = NAMED_DAYS.map((day) => cycleOfDay(YEAR, NOVEMBER, day));
  const unique = new Map([...recent, ...named].map((instant) => [instant.getTime(), instant]));
  return [...unique.values()].sort((first, second) => first.getTime() - second.getTime());
};

// The equity grows by one a day, so the gain of a span of days is the number of days between its first and last cycle.
const equityOf = (instant: Date): number =>
  INITIAL_CAPITAL + Math.round((instant.getTime() - Date.UTC(YEAR, 9, 1)) / DAY);

const closingOf = (cycle: Date): Date =>
  new Date(cycle.getFullYear(), cycle.getMonth(), cycle.getDate(), CLOSING_HOUR);

const tabs = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByRole('navigation', { name: FLOW_TABS });

const tab = (dashboard: DashboardPages, name: string): Locator =>
  tabs(dashboard).getByRole('link', { name, exact: true });

const intervalLabel = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByLabel('Intervallo scelto sul grafico');

const pointOfDay = (dashboard: DashboardPages, day: number): Locator =>
  dashboard
    .equityCurve()
    .locator(
      `circle[data-planned-at^="${apiInstant(cycleOfDay(YEAR, NOVEMBER, day)).slice(0, 16)}"]`,
    );

const openFlowSignedIn = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  path = '',
): Promise<void> => {
  await dashboard.open(`/flows/${fakePlatform.flowNamed(memory.flow).id}${path}`);
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.signInAs(account);
  }
  await expect(dashboard.flowName()).toHaveText(memory.flow);
};

const centreOf = async (locator: Locator): Promise<{ x: number; y: number }> => {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  return { x: (box?.x ?? 0) + (box?.width ?? 0) / 2, y: (box?.y ?? 0) + (box?.height ?? 0) / 2 };
};

const dragOnTheCurve = async (dashboard: DashboardPages, first: number, last: number) => {
  const start = await centreOf(pointOfDay(dashboard, first));
  const end = await centreOf(pointOfDay(dashboard, last));
  const mouse = dashboard.page.mouse;
  await mouse.move(start.x, start.y);
  await mouse.down();
  await mouse.move((start.x + end.x) / 2, start.y, { steps: 5 });
  await mouse.move(end.x, end.y, { steps: 5 });
  await mouse.up();
};

/** The days of the instants the rows of the cycles show, «16/11/2026, 10:15:00». */
const daysShown = async (dashboard: DashboardPages): Promise<Date[]> => {
  const cells = await dashboard
    .cycleRows()
    .evaluateAll((rows) => rows.map((row) => row.querySelector('td')?.textContent ?? ''));
  return cells
    .map((text) => /(\d{2})\/(\d{2})\/(\d{4})/.exec(text))
    .filter((match) => match !== null)
    .map((match) => new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1])));
};

Given(
  'che {string} ha il flusso {string} con cicli e posizioni chiuse negli ultimi 30 giorni',
  async ({ memory }, account: string, flow: string) => {
    const days = daysOfHistory();
    const last = days.at(-1) ?? new Date();
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      allocatedCapital: INITIAL_CAPITAL,
      currentCapital: equityOf(last),
      history: {
        closedPositions: days.map((cycle) => ({
          netPnl: 0.92,
          fees: 0.08,
          closedAt: closingOf(cycle),
        })),
        modelCalls: [],
      },
    });
    memory.flow = flow;
    memory.cycles = days.map((cycle) => aCompletedCycle(cycle));
    fakePlatform.recordCycles(flow, memory.cycles);
    days.forEach((cycle) => fakePlatform.recordEquity(flow, cycle, equityOf(cycle)));
    fakePlatform.recordClosedPositions(
      flow,
      days.map((cycle) => aClosedPosition({ closedAt: closingOf(cycle) })),
    );
    fakePlatform.holdPositions(flow, [anOpenPosition({ asset: 'ETH' })]);
  },
);

When(
  '{string} sceglie il periodo {string} nella pagina del flusso {string}',
  async ({ dashboard, memory }, account: string, period: string, flow: string) => {
    memory.flow = flow;
    await openFlowSignedIn(dashboard, memory, account);
    await dashboard.period().selectOption({ label: PERIODS[period] ?? period });
    await expect(dashboard.period().locator('option:checked')).toHaveText(PERIODS[period] ?? '');
  },
);

When('apre la scheda Cicli', async ({ dashboard }) => {
  await tab(dashboard, 'Cicli').click();
  await expect(tab(dashboard, 'Cicli')).toHaveAttribute('aria-current', 'page');
});

Then(
  "vede solo i cicli dell'ultima settimana e il periodo resta {string}",
  async ({ dashboard }, period: string) => {
    await expect(dashboard.cycleRows().first()).toBeVisible();
    const days = await daysShown(dashboard);
    const weekAgo = new Date(Date.now() - 8 * DAY);
    expect(days.length, 'the cycles of the week are shown').toBeGreaterThanOrEqual(7);
    expect(
      days.filter((day) => day.getTime() < weekAgo.getTime()),
      'no cycle before the week',
    ).toEqual([]);
    await expect(dashboard.period().locator('option:checked')).toHaveText(PERIODS[period] ?? '');
  },
);

When(
  "{string} trascina sull'equity curve dal {int} al {int} novembre 2026",
  async ({ dashboard, memory }, account: string, first: number, last: number) => {
    await openFlowSignedIn(dashboard, memory, account);
    await expect(pointOfDay(dashboard, first)).toBeVisible();
    await dragOnTheCurve(dashboard, first, last);
  },
);

Then(
  'riepilogo, grafico e statistiche valgono dal {int} al {int} novembre 2026',
  async ({ dashboard }, first: number, last: number) => {
    const gain = last - first;
    await expect(dashboard.page).toHaveURL(
      new RegExp(`from=${novemberDay(first)}&to=${novemberDay(last)}`),
    );
    await expect(dashboard.result('Guadagno nel periodo')).toHaveText(
      `+${gain},00 USDC · +0,${String(gain * 10).padStart(2, '0')}%`,
    );
    await expect(dashboard.equityPoints()).toHaveCount(last - first + 1);
    await expect(dashboard.statistic('Numero di operazioni')).toHaveText(String(last - first + 1));
  },
);

Then(
  "compare l'etichetta {string} con il comando per toglierla",
  async ({ dashboard }, label: string) => {
    await expect(intervalLabel(dashboard)).toContainText(label);
    await expect(
      intervalLabel(dashboard).getByRole('button', { name: REMOVE_INTERVAL }),
    ).toBeVisible();
  },
);

Given(
  "che {string} ha scelto l'intervallo dal {int} al {int} novembre 2026",
  async ({ dashboard, memory }, account: string, first: number, last: number) => {
    await openFlowSignedIn(dashboard, memory, account);
    await expect(pointOfDay(dashboard, first)).toBeVisible();
    await dragOnTheCurve(dashboard, first, last);
    await expect(intervalLabel(dashboard)).toBeVisible();
  },
);

When("toglie l'etichetta dell'intervallo", async ({ dashboard }) => {
  await intervalLabel(dashboard).getByRole('button', { name: REMOVE_INTERVAL }).click();
});

Then('la pagina torna al periodo del menu', async ({ dashboard, memory }) => {
  await expect(intervalLabel(dashboard)).toHaveCount(0);
  await expect(dashboard.page).not.toHaveURL(/from=|to=/);
  await expect(dashboard.period().locator('option:checked')).toHaveText('Tutta la vita');
  await expect(dashboard.equityPoints()).toHaveCount(memory.cycles.length);
});

Given(
  "che {string} è sulla scheda Posizioni chiuse con l'intervallo dal {int} al {int} novembre 2026",
  async ({ dashboard, memory }, account: string, first: number, last: number) => {
    await openFlowSignedIn(dashboard, memory, account);
    await expect(pointOfDay(dashboard, first)).toBeVisible();
    await dragOnTheCurve(dashboard, first, last);
    await expect(intervalLabel(dashboard)).toBeVisible();
    await tab(dashboard, 'Posizioni chiuse').click();
    await expect(dashboard.closedPositionRows()).toHaveCount(last - first + 1);
  },
);

Then('vede ancora la scheda Posizioni chiuse con lo stesso intervallo', async ({ dashboard }) => {
  await expect(tab(dashboard, 'Posizioni chiuse')).toHaveAttribute('aria-current', 'page');
  await expect(intervalLabel(dashboard)).toContainText('dal 10/11/2026 al 12/11/2026');
  await expect(dashboard.closedPositionRows()).toHaveCount(3);
});

Given(
  'che il ciclo del {word} alle {word} del flusso {string} è fallito',
  async ({ memory }, date: string, time: string, flow: string) => {
    const [day = 0, month = 0, year = 0] = date.split('/').map(Number);
    const [hours = 0, minutes = 0] = time.split(':').map(Number);
    const plannedAt = apiInstant(new Date(year, month - 1, day, hours, minutes));
    memory.cycles = memory.cycles.map((cycle) =>
      cycle.planned_at === plannedAt
        ? aFailedCycle(cycle, STEPS.agentDecision, {
            errorType: 'ModelCallTimeoutError',
            message: 'il modello non ha risposto',
          })
        : cycle,
    );
    expect(memory.cycles.filter((cycle) => cycle.outcome === 'fallito')).toHaveLength(1);
    fakePlatform.recordCycles(flow, memory.cycles);
  },
);

When(
  "{string} sceglie il suo segno sull'equity curve",
  async ({ dashboard, memory }, account: string) => {
    memory.chosenCycle = memory.cycles.find((cycle) => cycle.outcome === 'fallito');
    await openFlowSignedIn(dashboard, memory, account);
    await dashboard
      .equityCurve()
      .getByRole('link', { name: /^Ciclo fallito del / })
      .click();
  },
);

Then("la pagina non mostra l'elenco dei cicli recenti", async ({ dashboard }) => {
  await expect(dashboard.equityPoints().first()).toBeVisible();
  await dashboard.waitUntilRead();
  await expect(dashboard.page.getByRole('list', { name: 'Cicli recenti' })).toHaveCount(0);
  await expect(dashboard.page.getByRole('heading', { name: 'Cicli recenti' })).toHaveCount(0);
});

When(
  '{string} sceglie Configurazione nella pagina del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    memory.flow = flow;
    await openFlowSignedIn(dashboard, memory, account);
    await dashboard.content().getByRole('link', { name: 'Configurazione', exact: true }).click();
  },
);

Then(
  'vede configurazione, versioni e i comandi Modifica, Duplica ed Esporta, senza il periodo',
  async ({ dashboard, memory }) => {
    await expect(dashboard.pageHeading()).toHaveText(`Configurazione di ${memory.flow}`);
    await expect(dashboard.page.getByLabel('Configurazione', { exact: true })).toBeVisible();
    await expect(dashboard.versions()).toBeVisible();
    await expect(
      dashboard.content().getByRole('link', { name: 'Modifica', exact: true }),
    ).toBeVisible();
    await expect(dashboard.button('Duplica')).toBeVisible();
    await expect(dashboard.button('Esporta')).toBeVisible();
    await expect(dashboard.period()).toHaveCount(0);
  },
);

When(
  '{string} apre la Panoramica del flusso {string} con il periodo {string}',
  async ({ dashboard, memory }, account: string, flow: string, period: string) => {
    memory.flow = flow;
    await openFlowSignedIn(dashboard, memory, account);
    await dashboard.period().selectOption({ label: PERIODS[period] ?? period });
    await expect(tab(dashboard, 'Panoramica')).toHaveAttribute('aria-current', 'page');
  },
);

Then(
  'le posizioni aperte sono quelle attuali e la pagina lo dice',
  async ({ dashboard, memory }) => {
    const held = fakePlatform.openPositionsOf(fakePlatform.flowNamed(memory.flow).id);
    const section = dashboard.content().getByRole('region', { name: 'Posizioni aperte attuali' });
    await expect(section).toContainText('qualunque sia il periodo');
    await expect(dashboard.openPositionRows()).toHaveCount(held.length);
    await expect(dashboard.cell(dashboard.openPositionRows().first(), 'Asset')).toContainText(
      'ETH',
    );
  },
);
