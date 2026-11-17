import { expect, type Locator } from '@playwright/test';

import { aCompletedCycle, STEPS, type FakeCycle } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';

import { colourOf, isAmber, isGreen, isRed, type Rgb } from '../../../support/colours';
import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

const PLANNED_AT = new Date('2026-11-14T09:00:00Z');

// The icons by the words of the scenarios, as the shared icons name them (ADR icone-con-lucide-react-e-comandi-condivisi).
const ICONS: Readonly<Record<string, string>> = {
  pausa: 'pause',
  play: 'play',
  quadrato: 'square',
  'freccia in su': 'arrow-up',
  'freccia in giù': 'arrow-down',
  più: 'plus',
  x: 'x',
  'frecce circolari': 'refresh',
};

const COLOURS: Readonly<Record<string, (colour: Rgb) => boolean>> = {
  verde: isGreen,
  ambra: isAmber,
  rosso: isRed,
};

// The status of the flow in which the command is offered (R2.3.4).
const STATUS_OFFERING: Readonly<Record<string, string>> = {
  Pausa: 'attivo',
  Stop: 'attivo',
  Riprendi: 'in pausa',
  Avvia: 'fermo',
};

const DIRECTIONS = ['long', 'short'];

// Commands, actions and the direction of the opening the cycles tab of the flow shows.
const ICONS_ON_THE_CYCLES = 6;

const iconNamed = (words: string): string => {
  const icon = ICONS[words];
  expect(icon, `icona «${words}»`).toBeDefined();
  return icon ?? '';
};

/** A cycle in which the agent took every action it can, one per asset (R1.4.3, R3.1.3). */
const aCycleWithEveryAction = (): FakeCycle => {
  const cycle = aCompletedCycle(PLANNED_AT, 'BTC');
  return {
    ...cycle,
    documents: cycle.documents.map((document) => {
      if (document.step !== STEPS.agentDecision) {
        return document;
      }
      const [opening] = document.content.decisioni as unknown[];
      return {
        ...document,
        content: {
          ...document.content,
          decisioni: [
            opening,
            { tipo: 'Decision', asset: 'ETH', action: 'chiudi', reasoning: 'obiettivo raggiunto' },
            { tipo: 'Decision', asset: 'SOL', action: 'mantieni', reasoning: 'laterale' },
            { tipo: 'Decision', asset: 'XRP', action: 'aggiorna', reasoning: 'stop più vicino' },
          ],
        },
      };
    }),
  };
};

/** Opens a page as the user: the first page asks to sign in and brings the user back to it. */
const openSignedIn = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  open: () => Promise<void>,
): Promise<void> => {
  await open();
  if (memory.account !== memory.tradingAccount) {
    await dashboard.signInAs(memory.tradingAccount);
    memory.account = memory.tradingAccount;
  }
  await dashboard.waitUntilRead();
};

/** The label that shows the text, with its icon inside. */
const labelled = (dashboard: DashboardPages, text: string): Locator =>
  dashboard.content().getByText(text, { exact: true }).first();

Given(
  'che {string} ha il flusso attivo {string} con posizioni e cicli',
  ({ memory }, user: string, flow: string) => {
    fakePlatform.ensureUser(user);
    fakePlatform.addFlow(user, flow, { status: 'attivo' });
    fakePlatform.holdPositions(flow, [
      anOpenPosition({ asset: 'BTC', side: 'long' }),
      anOpenPosition({ asset: 'ETH', side: 'short' }),
    ]);
    fakePlatform.recordCycles(flow, [aCycleWithEveryAction()]);
    memory.tradingAccount = user;
    memory.flow = flow;
  },
);

When(
  '{string} apre la pagina di un flusso in cui è disponibile il comando {word}',
  async ({ dashboard, memory }, user: string, command: string) => {
    expect(user).toBe(memory.tradingAccount);
    const status = STATUS_OFFERING[command];
    expect(status, `stato che offre ${command}`).toBeDefined();
    fakePlatform.changeFlow(memory.flow, { status });
    await openSignedIn(dashboard, memory, () => dashboard.openFlow(memory.flow));
  },
);

Then(
  /^il comando (\S+) è (\S+) con l'icona (.+) e il testo "([^"]*)"$/,
  async ({ dashboard }, command: string, colour: string, icon: string, text: string) => {
    const button = dashboard.flowCommand(command);
    const isOfColour = COLOURS[colour];
    expect(isOfColour, `colore «${colour}»`).toBeDefined();
    expect(isOfColour?.(await colourOf(button, 'backgroundColor'))).toBe(true);
    await expect(button.locator('svg')).toHaveAttribute('data-icon', iconNamed(icon));
    await expect(button).toHaveText(text);
  },
);

When(
  '{string} guarda una decisione o una posizione con {word}',
  async ({ dashboard, memory }, user: string, value: string) => {
    expect(user).toBe(memory.tradingAccount);
    // The directions show on the positions of the flow, the actions on the decisions of its cycles.
    const open = DIRECTIONS.includes(value)
      ? () => dashboard.openPositionsOf(memory.flow)
      : () => dashboard.openCyclesOf(memory.flow);
    await openSignedIn(dashboard, memory, open);
  },
);

Then(
  /^accanto al testo "([^"]*)" vede l'icona (.+)$/,
  async ({ dashboard }, value: string, icon: string) => {
    const label = labelled(dashboard, value);
    await expect(label).toBeVisible();
    await expect(label.locator('svg')).toHaveAttribute('data-icon', iconNamed(icon));
  },
);

When(
  "un lettore di schermo legge un comando, un'azione o una direzione",
  async ({ dashboard, memory }) => {
    await openSignedIn(dashboard, memory, () => dashboard.openCyclesOf(memory.flow));
  },
);

Then("legge il suo nome e non il nome dell'icona", async ({ dashboard }) => {
  await expect(dashboard.flowCommand('Pausa')).toHaveAccessibleName('Pausa');
  await expect(dashboard.flowCommand('Stop')).toHaveAccessibleName('Stop');
  await expect(dashboard.cycleRows().first()).toContainText('apri long BTC');
  const icons = dashboard.content().locator('svg[data-icon]');
  expect(await icons.count()).toBeGreaterThanOrEqual(ICONS_ON_THE_CYCLES);
  for (const icon of await icons.all()) {
    await expect(icon).toHaveAttribute('aria-hidden', 'true');
    await expect(icon).not.toHaveAttribute('aria-label');
    await expect(icon.locator('title')).toHaveCount(0);
  }
});
