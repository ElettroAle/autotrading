import { expect, type Locator } from '@playwright/test';

import { paths } from '@/config/paths';
import {
  aCompletedCycle,
  withDecisions,
  type FakeCycle,
  type FakeDecision,
} from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { formatInstant } from '@/utils/format-instant';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// R6.5.5 on the tab Decisioni of the page of the flow; pytest-bdd runs the same scenarios on the use cases (ADR
// storico-delle-decisioni-nell-api, ADR scheda-decisioni-nella-pagina-del-flusso).

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const SHORTENED_LENGTH = 160;
const READ_ALL = /\s*Leggi tutto$/;
// A cycle older than the week, so the period of 7 days has decisions to leave out.
const OLDER_DAYS = 10;
const REASONING =
  'Il prezzo ha rotto la resistenza con volumi in aumento e il sentiment resta positivo: la decisione segue il ' +
  'trend del giorno con leva contenuta e uno stop sotto il minimo della giornata.';
// The words of the actions as the user chooses them among the filters.
const ACTION_LABELS: Record<string, string> = {
  apri: 'Apri',
  chiudi: 'Chiudi',
  mantieni: 'Mantieni',
  aggiorna: 'Aggiorna',
};

type DayDecision = readonly [action: string, direction: string | null];

// What the agent decided each day on BTC and ETH, from the latest back: every action and direction somewhere.
const BTC_DAYS: readonly DayDecision[] = [
  ['apri', 'long'],
  ['mantieni', null],
  ['chiudi', null],
  ['apri', 'short'],
  ['mantieni', null],
  ['aggiorna', null],
  ['apri', 'long'],
];
const ETH_DAYS: readonly DayDecision[] = [
  ['mantieni', null],
  ['apri', 'long'],
  ['mantieni', null],
  ['chiudi', null],
  ['apri', 'short'],
  ['mantieni', null],
  ['mantieni', null],
];

const aDecision = (asset: string, [action, direction]: DayDecision, confidence: number) =>
  ({
    asset,
    action,
    reasoning: REASONING,
    confidence,
    opening: direction === null ? null : { direction },
  }) satisfies FakeDecision;

/** The cycles of the background, newest first, the older one last. */
const cyclesOfTheWeek = (): FakeCycle[] => {
  const latest = Date.now() - HOUR;
  const week = BTC_DAYS.map((btc, day) =>
    withDecisions(aCompletedCycle(new Date(latest - day * DAY)), [
      aDecision('BTC', btc, 60 + day),
      aDecision('ETH', ETH_DAYS[day] ?? ['mantieni', null], 50 + day),
    ]),
  );
  const older = withDecisions(aCompletedCycle(new Date(latest - OLDER_DAYS * DAY)), [
    aDecision('BTC', ['apri', 'long'], 80),
    aDecision('ETH', ['mantieni', null], 30),
  ]);
  return [...week, older];
};

const decisionsOf = (memory: ScenarioMemory) =>
  memory.cycles.flatMap(
    (cycle) =>
      (cycle.documents.find((document) => Array.isArray(document.content.decisioni))?.content
        .decisioni ?? []) as FakeDecision[],
  );

const table = (dashboard: DashboardPages): Locator =>
  dashboard.page.getByRole('table', { name: 'Decisioni', exact: true });

const rows = (dashboard: DashboardPages): Locator => table(dashboard).locator('tbody tr');

const cellTexts = async (dashboard: DashboardPages, header: string): Promise<string[]> =>
  Promise.all(
    (await rows(dashboard).all()).map(async (row) =>
      ((await dashboard.cell(row, header).textContent()) ?? '').replace(header, ''),
    ),
  );

const choice = (dashboard: DashboardPages, group: string, name: string): Locator =>
  dashboard.page
    .getByRole('group', { name: group, exact: true })
    .getByRole('button', { name, exact: true });

/** From the page of the flow to its tab Decisioni, as a user gets there. */
const openHistory = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  flow: string,
): Promise<void> => {
  memory.flow = flow;
  await dashboard.openFlowAs(account, flow);
  await dashboard.page.getByRole('link', { name: 'Decisioni', exact: true }).click();
  await expect(rows(dashboard).first()).toBeVisible();
};

Given(
  'che {string} ha il flusso {string} con cicli conclusi negli ultimi 7 giorni su BTC ed ETH',
  async ({ memory }, account: string, flow: string) => {
    fakePlatform.giveFlowTo(account, flow);
    fakePlatform.changeFlow(flow, { assets: ['BTC', 'ETH'] });
    memory.cycles = cyclesOfTheWeek();
    fakePlatform.recordCycles(flow, memory.cycles);
    memory.flow = flow;
    memory.periodPage = paths.flowDecisions.getHref(fakePlatform.flowNamed(flow).id);
  },
);

When(
  '{string} apre lo storico delle decisioni del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await openHistory(dashboard, memory, account, flow);
  },
);

When(
  '{string} filtra lo storico per asset {string} e azione {string}',
  async ({ dashboard, memory }, account: string, asset: string, action: string) => {
    await openHistory(dashboard, memory, account, memory.flow);
    await choice(dashboard, 'Asset', asset).click();
    await expect(choice(dashboard, 'Asset', asset)).toHaveAttribute('aria-pressed', 'true');
    const label = ACTION_LABELS[action] ?? action;
    await choice(dashboard, 'Azione', label).click();
    await expect(choice(dashboard, 'Azione', label)).toHaveAttribute('aria-pressed', 'true');
    await dashboard.waitUntilRead();
  },
);

When('{string} sceglie una riga dello storico', async ({ dashboard, memory }, account: string) => {
  await openHistory(dashboard, memory, account, memory.flow);
  // The fourth row is the decision on ETH of the second cycle: neither the first nor the last cycle.
  memory.chosenCycle = memory.cycles[1];
  const row = rows(dashboard).nth(3);
  await expect(dashboard.cell(row, 'Asset')).toContainText('ETH');
  // A press on the row, away from the link of its first cell, opens the detail too.
  await dashboard.cell(row, 'Ragionamento').click();
});

Then(
  'vede una riga per ciclo e asset con istante, asset, azione, direzione, confidenza e ragionamento accorciato',
  async ({ dashboard, memory }) => {
    await expect(rows(dashboard)).toHaveCount(decisionsOf(memory).length);
    const expectedInstants = memory.cycles.flatMap((cycle) => [
      formatInstant(cycle.planned_at),
      formatInstant(cycle.planned_at),
    ]);
    expect(await cellTexts(dashboard, 'Istante')).toEqual(expectedInstants);
    expect(await cellTexts(dashboard, 'Asset')).toEqual(
      memory.cycles.flatMap(() => ['BTC', 'ETH']),
    );
    const first = rows(dashboard).first();
    await expect(dashboard.cell(first, 'Azione')).toContainText('apri');
    await expect(dashboard.cell(first, 'Direzione')).toContainText('long');
    await expect(dashboard.cell(first, 'Confidenza')).toContainText('60');
    // The command «Leggi tutto» beside the shortened text opens it whole (ADR testo-lungo-espandibile).
    const reasoning = ((await cellTexts(dashboard, 'Ragionamento'))[0] ?? '').replace(READ_ALL, '');
    expect(reasoning.endsWith('…')).toBe(true);
    expect(reasoning.length).toBeLessThanOrEqual(SHORTENED_LENGTH + 1);
    expect(REASONING.startsWith(reasoning.slice(0, -1))).toBe(true);
  },
);

Then('le più recenti in alto', async ({ dashboard, memory }) => {
  const newest = memory.cycles[0];
  await expect(dashboard.cell(rows(dashboard).first(), 'Istante')).toContainText(
    formatInstant(newest?.planned_at ?? ''),
  );
  const oldest = memory.cycles.at(-1);
  await expect(dashboard.cell(rows(dashboard).last(), 'Istante')).toContainText(
    formatInstant(oldest?.planned_at ?? ''),
  );
});

Then('vede solo le decisioni di aprire su {word}', async ({ dashboard, memory }, asset: string) => {
  const expected = decisionsOf(memory).filter(
    (decision) => decision.asset === asset && decision.action === 'apri',
  );
  await expect(rows(dashboard)).toHaveCount(expected.length);
  expect(await cellTexts(dashboard, 'Asset')).toEqual(expected.map(() => asset));
  expect(await cellTexts(dashboard, 'Azione')).toEqual(expected.map(() => 'apri'));
});

Then('lo storico mostra solo le decisioni degli ultimi 7 giorni', async ({ dashboard, memory }) => {
  const inWeek = memory.cycles.filter(
    (cycle) => Date.parse(cycle.planned_at) >= Date.now() - 7 * DAY,
  );
  await expect(rows(dashboard)).toHaveCount(inWeek.length * 2);
  await expect(dashboard.content().getByText(`${inWeek.length * 2} decisioni`)).toBeVisible();
  const older = formatInstant(memory.cycles.at(-1)?.planned_at ?? '');
  expect(await cellTexts(dashboard, 'Istante')).not.toContain(older);
});

Then('apre il dettaglio del ciclo di quella decisione', async ({ dashboard, memory }) => {
  const chosen = memory.chosenCycle;
  expect(chosen).toBeDefined();
  const href = paths.cycle.getHref(
    fakePlatform.flowNamed(memory.flow).id,
    chosen?.planned_at ?? '',
  );
  await dashboard.page.waitForURL((url) => url.pathname.endsWith(href));
  await expect(
    dashboard.page.getByText(formatInstant(chosen?.planned_at ?? '')).first(),
  ).toBeVisible();
});

const DIRECTION_LABELS: Record<string, string> = { long: 'Long', short: 'Short' };

When(
  '{string} filtra lo storico per direzione {string}',
  async ({ dashboard, memory }, account: string, direction: string) => {
    await openHistory(dashboard, memory, account, memory.flow);
    const label = DIRECTION_LABELS[direction] ?? direction;
    await choice(dashboard, 'Direzione', label).click();
    await expect(choice(dashboard, 'Direzione', label)).toHaveAttribute('aria-pressed', 'true');
    await dashboard.waitUntilRead();
  },
);

Then(
  'vede solo le decisioni di aprire {word}',
  async ({ dashboard, memory }, direction: string) => {
    const expected = decisionsOf(memory).filter(
      (decision) => decision.opening?.direction === direction,
    );
    await expect(rows(dashboard)).toHaveCount(expected.length);
    expect(await cellTexts(dashboard, 'Azione')).toEqual(expected.map(() => 'apri'));
    expect(await cellTexts(dashboard, 'Direzione')).toEqual(expected.map(() => direction));
  },
);

Given(
  "che il flusso {string} ha altri {int} cicli conclusi nell'ultimo giorno su BTC ed ETH",
  ({ memory }, flow: string, count: number) => {
    const [newest, ...older] = memory.cycles;
    const newestAt = Date.parse(newest?.planned_at ?? '');
    // One an hour before the newest, after the cycle of the day before: the oldest stay on the last page.
    const added = Array.from({ length: count }, (_, index) =>
      withDecisions(aCompletedCycle(new Date(newestAt - (index + 1) * HOUR)), [
        aDecision('BTC', ['mantieni', null], 40),
        aDecision('ETH', ['mantieni', null], 40),
      ]),
    );
    memory.cycles = [...(newest === undefined ? [] : [newest]), ...added, ...older];
    fakePlatform.recordCycles(flow, memory.cycles);
  },
);

When(
  '{string} apre la seconda pagina dello storico delle decisioni',
  async ({ dashboard, memory }, account: string) => {
    await openHistory(dashboard, memory, account, memory.flow);
    await dashboard.page.getByRole('link', { name: 'Pagina successiva' }).click();
    await expect(dashboard.content().getByText('Pagina 2')).toBeVisible();
  },
);

Then(
  'vede le {int} decisioni più vecchie, dalla più recente',
  async ({ dashboard, memory }, count: number) => {
    const instants = memory.cycles.flatMap((cycle) => [
      formatInstant(cycle.planned_at),
      formatInstant(cycle.planned_at),
    ]);
    await expect(rows(dashboard)).toHaveCount(count);
    expect(await cellTexts(dashboard, 'Istante')).toEqual(instants.slice(-count));
    await expect(dashboard.page.getByRole('link', { name: 'Pagina successiva' })).toHaveCount(0);
  },
);
