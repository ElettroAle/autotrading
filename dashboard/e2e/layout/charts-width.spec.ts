import { expect, test, type Locator, type Page } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const PHONE = { width: 360, height: 780 } as const;
const POINTS = 200;
const HOUR = 60 * 60 * 1000;
const INITIAL_CAPITAL = 1000;
// Names with no room to break on a phone: the legend and the tooltip wrap them instead of leaving the screen.
const FLOWS = [
  'flusso-con-un-nome-lunghissimo-che-non-sta-in-una-riga',
  'secondo-flusso-con-un-nome-altrettanto-lungo-da-leggere',
] as const;

type ChartLayout = {
  readonly figureWidth: number;
  readonly figureScrolls: boolean;
  readonly chartWidth: number;
  readonly pageWidth: number;
  readonly overlappingDates: number;
};

type Box = { readonly left: number; readonly right: number };

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

const recordCycles = (flow: string): void => {
  const now = Date.now();
  for (let index = 0; index < POINTS; index += 1) {
    const instant = new Date(now - (POINTS - index) * HOUR);
    fakePlatform.recordEquity(flow, instant, INITIAL_CAPITAL + (index % 9) - 4);
  }
};

const layoutOf = (figure: Locator): Promise<ChartLayout> =>
  figure.evaluate((element) => {
    const chart = element.querySelector('svg.recharts-surface');
    const dates = [
      ...element.querySelectorAll('.recharts-xAxis .recharts-cartesian-axis-tick text'),
    ]
      .map((date) => date.getBoundingClientRect())
      .toSorted((first, second) => first.left - second.left);
    return {
      figureWidth: element.clientWidth,
      figureScrolls: element.scrollWidth > element.clientWidth,
      chartWidth: chart?.getBoundingClientRect().width ?? Number.POSITIVE_INFINITY,
      pageWidth: document.documentElement.scrollWidth,
      overlappingDates: dates.filter(
        (date, index) => index > 0 && date.left < (dates[index - 1]?.right ?? date.left),
      ).length,
    };
  });

const expectWithinTheScreen = (layout: ChartLayout): void => {
  expect(layout.figureScrolls, 'the chart does not scroll sideways').toBe(false);
  expect(layout.chartWidth, 'the chart is as wide as its room').toBeLessThanOrEqual(
    layout.figureWidth,
  );
  expect(layout.pageWidth, 'the page does not scroll sideways').toBeLessThanOrEqual(PHONE.width);
  expect(layout.overlappingDates, 'the dates of the axis thin out').toBe(0);
};

// A finger near the right edge of the plot, where a tooltip that could leave the chart would.
const tooltipNearTheRightEdge = async (page: Page, figure: Locator): Promise<Box> => {
  const plot = figure.locator('.recharts-cartesian-grid');
  await plot.scrollIntoViewIfNeeded();
  const area = await plot.boundingBox();
  expect(area, 'the chart has a plot').not.toBeNull();
  const { x, y, width, height } = area ?? { x: 0, y: 0, width: 0, height: 0 };
  await page.touchscreen.tap(x + width - 4, y + height / 2);
  const tooltip = figure.locator('.recharts-tooltip-wrapper .recharts-default-tooltip');
  await expect(tooltip).toBeVisible();
  const box = await tooltip.boundingBox();
  return { left: box?.x ?? -1, right: (box?.x ?? 0) + (box?.width ?? Number.POSITIVE_INFINITY) };
};

// ADR grafici-condivisi-larghi-come-lo-schermo: on a screen 360 pixels wide every chart is as wide as its room, with
// nothing to scroll sideways, dates that thin out and a tooltip wholly inside the screen.
test.describe('ADR grafici-condivisi-larghi-come-lo-schermo: every chart within a screen 360 pixels wide', () => {
  test('the overlaid equity curves stay within the screen, tooltip included', async ({ page }) => {
    const dashboard = new DashboardPages(page);
    await page.setViewportSize(PHONE);
    fakePlatform.ensureUser(ACCOUNT);
    const ids = FLOWS.map((flow) => {
      fakePlatform.addFlow(ACCOUNT, flow, { allocatedCapital: INITIAL_CAPITAL });
      recordCycles(flow);
      return fakePlatform.flowNamed(flow).id;
    });
    await dashboard.open(`/comparison?${ids.map((id) => `flow=${id}`).join('&')}`);
    await dashboard.signInAs(ACCOUNT);
    await expect(dashboard.comparisonPoints(FLOWS[0])).toHaveCount(POINTS);

    expectWithinTheScreen(await layoutOf(dashboard.comparisonChart()));
    const tooltip = await tooltipNearTheRightEdge(page, dashboard.comparisonChart());
    expect(tooltip.left, 'the tooltip starts inside the screen').toBeGreaterThanOrEqual(0);
    expect(tooltip.right, 'the tooltip ends inside the screen').toBeLessThanOrEqual(PHONE.width);
  });

  test('the equity curve of a flow stays within the screen, tooltip included', async ({ page }) => {
    const dashboard = new DashboardPages(page);
    await page.setViewportSize(PHONE);
    fakePlatform.ensureUser(ACCOUNT);
    fakePlatform.addFlow(ACCOUNT, FLOWS[0], { allocatedCapital: INITIAL_CAPITAL });
    recordCycles(FLOWS[0]);
    await dashboard.openFlowAs(ACCOUNT, FLOWS[0]);
    await expect(dashboard.equityPoints()).toHaveCount(POINTS);

    expectWithinTheScreen(await layoutOf(dashboard.equityCurve()));
    const tooltip = await tooltipNearTheRightEdge(page, dashboard.equityCurve());
    expect(tooltip.left, 'the tooltip starts inside the screen').toBeGreaterThanOrEqual(0);
    expect(tooltip.right, 'the tooltip ends inside the screen').toBeLessThanOrEqual(PHONE.width);
  });
});
