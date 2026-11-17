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
