import { expect, type Locator } from '@playwright/test';

import { aCapitalChange } from '@/testing/mocks/capital-changes';
import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { isGreen, isRed, type Rgb } from '../../../support/colours';
import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When } from '../../../support/fixtures';

// R6.5.6, ADR legenda-condivisa-dei-grafici: the legend below the equity curve of the flow, with the marks of the chart.

const INITIAL_CAPITAL = 1000;
const HOUR = 60 * 60_000;
const PHONE = { width: 360, height: 780 } as const;
// Above and below the initial capital, so the curve has points of both colours.
const EQUITIES = [1000, 1020, 990, 1010] as const;

type Shape = 'circle' | 'line' | 'path';

type Mark = {
  readonly shape: Shape;
  readonly fill: Rgb;
  readonly stroke: Rgb;
  readonly dashed: boolean;
  readonly strokes: number;
  readonly closed: boolean;
};

const hoursAgo = (hours: number): Date => new Date(Date.now() - hours * HOUR);

// A violet tone: much blue, some red and little green, as the mark of a change of the capital.
const isViolet = ({ red, green, blue }: Rgb): boolean =>
  blue > 150 && red > 1.5 * green && blue > 2 * green;

const legend = (dashboard: DashboardPages): Locator =>
  dashboard.equityCurve().getByRole('list', { name: 'Legenda' });

const entry = (dashboard: DashboardPages, label: string): Locator =>
  legend(dashboard)
    .getByRole('listitem')
    .filter({ hasText: new RegExp(`^${label}$`) });

/** The mark beside the name of an entry, as the browser paints it. */
const markOf = (dashboard: DashboardPages, label: string): Promise<Mark> =>
  entry(dashboard, label)
    .locator('svg > *')
    .first()
    .evaluate((shape) => {
      const style = getComputedStyle(shape);
      const rgb = (colour: string): Rgb => {
        const [red = 0, green = 0, blue = 0, alpha = 1] = (colour.match(/[\d.]+/g) ?? []).map(
          Number,
        );
        return { red, green, blue, alpha: colour === 'none' ? 0 : alpha * 255 };
      };
      const path = shape.getAttribute('d') ?? '';
      return {
        shape: shape.tagName as Shape,
        fill: rgb(style.fill),
        stroke: rgb(style.stroke),
        dashed: style.strokeDasharray !== 'none',
        strokes: (path.match(/M/g) ?? []).length,
        closed: path.endsWith('Z'),
      };
    });

const expectEntry = async (dashboard: DashboardPages, label: string): Promise<Mark> => {
  await expect(entry(dashboard, label)).toBeVisible();
  return markOf(dashboard, label);
};

Given(
  'che {string} ha il flusso attivo {string} con cicli nel periodo mostrato',
  ({ memory }, account: string, flow: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      status: 'attivo',
      allocatedCapital: INITIAL_CAPITAL,
      currentCapital: INITIAL_CAPITAL,
    });
    EQUITIES.forEach((equity, index) =>
      fakePlatform.recordEquity(flow, hoursAgo(EQUITIES.length - index), equity),
    );
    memory.flow = flow;
  },
);

Given(
  'che {string} ha un ciclo fallito e una variazione di capitale nel periodo mostrato',
  ({}, flowName: string) => {
    const flow = fakePlatform.flowNamed(flowName);
    const failed = aFailedCycle(aCompletedCycle(hoursAgo(2.5)), STEPS.agentDecision, {
      errorType: 'ModelUnavailableError',
      message: 'fornitore IA non raggiungibile',
    });
    fakePlatform.recordCycles(flowName, [failed]);
    fakePlatform.recordCapitalChange(
      aCapitalChange(flow, INITIAL_CAPITAL, INITIAL_CAPITAL + 100, hoursAgo(1.5)),
    );
  },
);

When(
  '{string} apre la pagina del flusso {string} su un telefono',
  async ({ dashboard, memory }, account: string, flow: string) => {
    await dashboard.page.setViewportSize(PHONE);
    memory.account = account;
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

Then(
  `sotto l'equity curve la legenda mostra "sopra il capitale iniziale", "sotto il capitale iniziale" e "capitale iniziale", ciascuna col suo segno`,
  async ({ dashboard }) => {
    const chart = await dashboard.equityCurve().locator('svg.recharts-surface').boundingBox();
    const below = await legend(dashboard).boundingBox();
    expect(below?.y ?? 0).toBeGreaterThanOrEqual((chart?.y ?? 0) + (chart?.height ?? 0));
    const above = await expectEntry(dashboard, 'sopra il capitale iniziale');
    expect(above.shape).toBe('circle');
    expect(isGreen(above.fill)).toBe(true);
    const under = await expectEntry(dashboard, 'sotto il capitale iniziale');
    expect(under.shape).toBe('circle');
    expect(isRed(under.fill)).toBe(true);
    const baseline = await expectEntry(dashboard, 'capitale iniziale');
    expect(baseline.shape).toBe('line');
    expect(baseline.dashed).toBe(true);
  },
);

Then('la legenda non mostra "ciclo fallito" né "variazione di capitale"', async ({ dashboard }) => {
  await expect(legend(dashboard).getByRole('listitem')).toHaveCount(3);
  await expect(entry(dashboard, 'ciclo fallito')).toHaveCount(0);
  await expect(entry(dashboard, 'variazione di capitale')).toHaveCount(0);
});

Then(
  'la legenda mostra anche "ciclo fallito" con la croce rossa e "variazione di capitale" col rombo viola',
  async ({ dashboard }) => {
    const cross = await expectEntry(dashboard, 'ciclo fallito');
    expect(cross.shape).toBe('path');
    expect(cross.strokes).toBe(2);
    expect(isRed(cross.stroke)).toBe(true);
    const diamond = await expectEntry(dashboard, 'variazione di capitale');
    expect(diamond.shape).toBe('path');
    expect(diamond.closed).toBe(true);
    expect(isViolet(diamond.fill)).toBe(true);
  },
);

Then(
  'tutte le voci della legenda sono visibili senza scorrimento orizzontale',
  async ({ dashboard }) => {
    const entries = legend(dashboard).getByRole('listitem');
    await expect(entries).toHaveCount(5);
    expect(await dashboard.horizontalOverflow()).toBeLessThanOrEqual(0);
    for (const item of await entries.all()) {
      await expect(item).toBeVisible();
      const box = await item.boundingBox();
      expect(box?.x ?? -1).toBeGreaterThanOrEqual(0);
      expect((box?.x ?? 0) + (box?.width ?? Number.POSITIVE_INFINITY)).toBeLessThanOrEqual(
        PHONE.width,
      );
    }
  },
);

Given(
  'che {string} ha anche il flusso attivo {string} con cicli nel periodo mostrato',
  ({}, account: string, flow: string) => {
    fakePlatform.addFlow(account, flow, {
      status: 'attivo',
      allocatedCapital: INITIAL_CAPITAL,
      currentCapital: INITIAL_CAPITAL,
    });
    EQUITIES.forEach((equity, index) =>
      fakePlatform.recordEquity(flow, hoursAgo(EQUITIES.length - index), equity + 5),
    );
  },
);

Then(
  'sotto il grafico del confronto la legenda condivisa mostra {string} e {string}, ciascuno col segno della sua curva',
  async ({ dashboard }, first: string, second: string) => {
    const comparison = dashboard.comparisonChart().getByRole('list', { name: 'Legenda' });
    const chart = await dashboard.comparisonChart().locator('svg.recharts-surface').boundingBox();
    const below = await comparison.boundingBox();
    expect(below?.y ?? 0).toBeGreaterThanOrEqual((chart?.y ?? 0) + (chart?.height ?? 0));
    for (const flow of [first, second]) {
      // The mark of the shared legend: the dot of the curve, drawn around the origin of its own small drawing.
      const mark = dashboard.legendEntry(flow).locator('svg');
      await expect(mark).toHaveAttribute('viewBox', '-8 -8 16 16');
      await expect(mark.locator('circle')).toHaveCount(1);
      await expect(dashboard.comparisonPoints(flow).first()).toBeVisible();
    }
    const fills = await comparison
      .locator('svg > circle')
      .evaluateAll((dots) => dots.map((dot) => getComputedStyle(dot).fill));
    expect(new Set(fills).size).toBe(2);
  },
);
