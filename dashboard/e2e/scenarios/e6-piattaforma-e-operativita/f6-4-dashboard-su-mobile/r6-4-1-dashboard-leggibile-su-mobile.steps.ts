import { expect, type Locator } from '@playwright/test';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform, versionsWith } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import {
  aStoppedFlow,
  measurePages,
  preparePagesWithLongWords,
  signInOnTheFlows,
} from '../../../support/every-page';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The scenarios name no user: the user is one, signed in on the first page opened.
const USER = 'utente';
// The flow the scenarios open when they name none.
const THE_FLOW = 'prova-btc';
const SCREEN_HEIGHT = 800;
// The least a command or a view needs to be touched with a finger (ADR viste-e-comandi-della-pagina-del-flusso).
const TOUCHABLE_HEIGHT = 44;
const FLOW_VIEWS = [
  'Posizioni aperte',
  'Posizioni chiuse',
  'Cicli del flusso',
  'Versioni della configurazione',
];
const HISTORY_FILTERS = ['Flusso', 'Versione', 'Conto', 'Asset', 'Periodo'];
const NOON = Date.UTC(2026, 10, 14, 11, 0);
const HOUR = 3_600_000;

type Box = {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
};

const boxOf = async (locator: Locator): Promise<Box> => {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  return box ?? { x: 0, y: 0, width: 0, height: 0 };
};

type Rgb = { readonly red: number; readonly green: number; readonly blue: number };

// The browser writes colours in the space the style chose (oklch for Tailwind): painted on a canvas they read as RGB.
const colourOf = async (locator: Locator, property: 'color' | 'backgroundColor'): Promise<Rgb> => {
  const [red = 0, green = 0, blue = 0, alpha = 0] = await locator.evaluate((element, name) => {
    const context = document.createElement('canvas').getContext('2d');
    if (context === null) {
      return [];
    }
    context.fillStyle = getComputedStyle(element)[name];
    context.fillRect(0, 0, 1, 1);
    return [...context.getImageData(0, 0, 1, 1).data];
  }, property);
  // A transparent background shows the white of the page behind it.
  return alpha === 0 ? { red: 255, green: 255, blue: 255 } : { red, green, blue };
};

const isWhite = ({ red, green, blue }: Rgb): boolean => Math.min(red, green, blue) > 240;

// A red tone: the red channel well above the other two, as the commands that destroy.
const isRed = ({ red, green, blue }: Rgb): boolean => red > 150 && red > 2 * Math.max(green, blue);

/** The flow the scenario named, or the flow of the feature: a stopped flow of the user, created when missing. */
const flowOfScenario = (memory: ScenarioMemory, name = memory.flow || THE_FLOW): string => {
  memory.flow = name;
  fakePlatform.ensureUser(USER);
  if (!fakePlatform.flowsOf(USER).some((flow) => flow.name === name)) {
    aStoppedFlow(USER, name);
  }
  return name;
};

/** Opens a page as the user: the first page asks to sign in and brings the user back to it. */
const openSignedIn = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  open: () => Promise<void>,
): Promise<void> => {
  fakePlatform.ensureUser(USER);
  await open();
  if (memory.account !== USER) {
    memory.account = USER;
    await dashboard.signInAs(USER);
  }
};

const openFlowPage = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  name?: string,
): Promise<void> => {
  const flow = flowOfScenario(memory, name);
  await openSignedIn(dashboard, memory, () => dashboard.openFlow(flow));
  await expect(dashboard.flowName()).toHaveText(flow);
};

const filterLabel = (dashboard: DashboardPages, label: string): Locator =>
  dashboard.page
    .getByRole('group', { name: 'Filtri' })
    .locator('label')
    .filter({ hasText: new RegExp(`^${label}$`) });

Given('uno schermo largo {int} pixel', async ({ dashboard }, width: number) => {
  await dashboard.page.setViewportSize({ width, height: SCREEN_HEIGHT });
});

When("l'utente apre una qualsiasi pagina della dashboard", async ({ dashboard, memory }) => {
  const pages = preparePagesWithLongWords(USER, THE_FLOW);
  memory.account = USER;
  await signInOnTheFlows(dashboard, USER);
  memory.spilledByPage = await measurePages(dashboard, pages);
});

Then('la pagina non scorre in orizzontale', ({ memory }) => {
  expect([...memory.spilledByPage.keys()]).toContain('flow');
  expect(
    Object.fromEntries([...memory.spilledByPage].filter(([, spilled]) => spilled.length > 0)),
  ).toEqual({});
});

Given('il flusso {string} con il modello {string}', ({ memory }, flow: string, model: string) => {
  memory.flow = flow;
  aStoppedFlow(USER, flow, model);
});

When("l'utente apre la pagina del flusso", async ({ dashboard, memory }) => {
  await openFlowPage(dashboard, memory);
});

When("l'utente apre la pagina del flusso {string}", async ({ dashboard, memory }, flow: string) => {
  await openFlowPage(dashboard, memory, flow);
});

Then(
  'il nome del modello resta entro il riquadro ed è leggibile per intero',
  async ({ dashboard, memory }) => {
    const model = fakePlatform.flowNamed(memory.flow).model;
    const value = dashboard.detail('Modello');
    await expect(value).toHaveText(model);
    const frame = await boxOf(dashboard.page.getByRole('region', { name: memory.flow }));
    const box = await boxOf(value);
    expect(box.x).toBeGreaterThanOrEqual(frame.x);
    expect(box.x + box.width).toBeLessThanOrEqual(frame.x + frame.width);
    expect(
      await value.evaluate((element) => element.scrollWidth - element.clientWidth),
    ).toBeLessThanOrEqual(0);
  },
);

Then(
  'posizioni, cicli e versioni compaiono come schede o comandi separati da Modifica',
  async ({ dashboard }) => {
    const views = dashboard.content().getByRole('navigation', { name: 'Dati del flusso' });
    for (const view of FLOW_VIEWS) {
      const link = views.getByRole('link', { name: view, exact: true });
      await expect(link).toBeVisible();
      expect((await boxOf(link)).height).toBeGreaterThanOrEqual(TOUCHABLE_HEIGHT);
    }
    const edit = dashboard.content().getByRole('link', { name: 'Modifica la configurazione' });
    await expect(views.getByRole('link', { name: 'Modifica la configurazione' })).toHaveCount(0);
    await expect(edit).toBeVisible();
    expect((await boxOf(edit)).height).toBeGreaterThanOrEqual(TOUCHABLE_HEIGHT);
  },
);

Then('Avvia risalta come comando principale e Archivia come distruttivo', async ({ dashboard }) => {
  const start = dashboard.flowCommand('Avvia');
  const archive = dashboard.flowCommand('Archivia');
  const other = dashboard.page.getByRole('button', { name: 'Duplica', exact: true });
  expect(isWhite(await colourOf(start, 'backgroundColor'))).toBe(false);
  expect(isWhite(await colourOf(start, 'color'))).toBe(true);
  expect(isWhite(await colourOf(other, 'backgroundColor'))).toBe(true);
  expect(isRed(await colourOf(archive, 'color'))).toBe(true);
  expect(isRed(await colourOf(other, 'color'))).toBe(false);
});

Then(
  'il titolo è {string} e lo stato viene prima della configurazione',
  async ({ dashboard }, title: string) => {
    await expect(dashboard.pageHeading()).toHaveText(title);
    const status = await boxOf(dashboard.flowStatus());
    const configuration = await boxOf(dashboard.page.getByLabel('Configurazione', { exact: true }));
    expect(status.y + status.height).toBeLessThanOrEqual(configuration.y);
  },
);

When("l'utente apre i cicli del flusso {string}", async ({ dashboard, memory }, flow: string) => {
  flowOfScenario(memory, flow);
  await openSignedIn(dashboard, memory, () => dashboard.openCyclesOf(flow));
});

Then('la pagina mostra che sono i cicli di {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.pageHeading()).toHaveText(`Cicli di ${flow}`);
});

When("l'utente apre lo storico", async ({ dashboard, memory }) => {
  flowOfScenario(memory);
  await openSignedIn(dashboard, memory, () => dashboard.openHistory());
  await expect(dashboard.filter('Flusso').locator('option')).not.toHaveCount(1);
});

Then('ogni filtro ha la sua etichetta sopra il proprio campo', async ({ dashboard }) => {
  for (const label of HISTORY_FILTERS) {
    const caption = await boxOf(filterLabel(dashboard, label));
    const field = await boxOf(dashboard.filter(label));
    expect(caption.y + caption.height, label).toBeLessThanOrEqual(field.y);
    expect(Math.abs(caption.x - field.x), label).toBeLessThanOrEqual(1);
  }
});

Given('che il flusso {string} ha una sola versione', ({ memory }, flow: string) => {
  flowOfScenario(memory, flow);
  fakePlatform.changeFlow(flow, { version: 1, versions: versionsWith({}) });
});

When("l'utente apre le versioni della configurazione", async ({ dashboard, memory }) => {
  await openFlowPage(dashboard, memory);
  await dashboard.page.getByRole('link', { name: 'Versioni della configurazione' }).click();
  await expect(dashboard.versions()).toBeVisible();
});

Then('il comando Confronta è disattivato', async ({ dashboard }) => {
  await expect(dashboard.versions().getByRole('listitem')).toHaveCount(1);
  await expect(dashboard.button('Confronta')).toBeDisabled();
});

Given("che l'utente non ha collegato Telegram", () => {
  fakePlatform.ensureUser(USER);
  expect(fakePlatform.linkedChatOf(USER)).toBeUndefined();
});

When('apre la pagina Notifiche', async ({ dashboard, memory }) => {
  await openSignedIn(dashboard, memory, () => dashboard.openNotifications());
});

Then('legge i passi per collegare la chat con il codice', async ({ dashboard }) => {
  const steps = dashboard.page.getByRole('list', { name: 'Come collegare Telegram' });
  await expect(steps.getByRole('listitem')).toHaveText([
    /codice di collegamento/,
    /Invia il codice al bot/,
    /conferma/,
  ]);
});

When("l'utente apre l'elenco dei flussi", async ({ dashboard, memory }) => {
  const flow = flowOfScenario(memory);
  fakePlatform.recordCycles(flow, [
    aCompletedCycle(new Date(NOON)),
    aFailedCycle(aCompletedCycle(new Date(NOON - HOUR)), STEPS.agentDecision, {
      errorType: 'ModelCallTimeoutError',
      message: 'il modello non ha risposto',
    }),
  ]);
  await openSignedIn(dashboard, memory, () => dashboard.open());
  await expect(dashboard.recentOutcomes(flow).getByRole('listitem')).toHaveCount(2);
});

Then(
  'gli esiti dei cicli recenti hanno una legenda che dice concluso e fallito',
  async ({ dashboard }) => {
    const legend = dashboard.content().getByRole('list', { name: 'Legenda degli esiti' });
    await expect(legend.getByRole('listitem')).toHaveText([/concluso/, /fallito/]);
  },
);

Then("l'impaginazione su più colonne resta", async ({ dashboard }) => {
  const menu = await boxOf(dashboard.menu());
  const content = await boxOf(dashboard.content());
  expect(menu.x + menu.width).toBeLessThanOrEqual(content.x);
  const label = await boxOf(
    dashboard.page.getByLabel('Configurazione', { exact: true }).locator('dt').first(),
  );
  const value = await boxOf(dashboard.detail('Versione'));
  expect(label.x + label.width).toBeLessThanOrEqual(value.x);
  expect(Math.abs(label.y - value.y)).toBeLessThanOrEqual(1);
});
