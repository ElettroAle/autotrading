import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const FLOW = 'alfa';
const PHONE = { width: 360, height: 780 } as const;
const POINTS = 400;
const HOUR = 60 * 60 * 1000;
const INITIAL_CAPITAL = 1000;

type CurveLayout = {
  readonly figureWidth: number;
  readonly figureScrolls: boolean;
  readonly chartWidth: number;
  readonly pageWidth: number;
  readonly pointRadius: number;
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR equity-curve-larga-come-lo-schermo: on a screen 360 pixels wide the equity curve of a flow with many points is as
// wide as its room, with nothing to scroll sideways, and its points are smaller than with few.
test('ADR equity-curve-larga-come-lo-schermo: the equity curve with many points stays within a screen 360 pixels wide', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  await page.setViewportSize(PHONE);
  fakePlatform.ensureUser(ACCOUNT);
  fakePlatform.addFlow(ACCOUNT, FLOW, { allocatedCapital: INITIAL_CAPITAL });
  const now = Date.now();
  for (let index = 0; index < POINTS; index += 1) {
    const instant = new Date(now - (POINTS - index) * HOUR);
    fakePlatform.recordEquity(FLOW, instant, INITIAL_CAPITAL + (index % 9) - 4);
  }
  await dashboard.openFlowAs(ACCOUNT, FLOW);
  await expect(dashboard.equityPoints()).toHaveCount(POINTS);

  const layout: CurveLayout = await dashboard.equityCurve().evaluate((figure) => {
    const chart = figure.querySelector('svg.recharts-surface');
    const point = figure.querySelector('circle[data-planned-at]');
    return {
      figureWidth: figure.clientWidth,
      figureScrolls: figure.scrollWidth > figure.clientWidth,
      chartWidth: chart?.getBoundingClientRect().width ?? Number.POSITIVE_INFINITY,
      pageWidth: document.documentElement.scrollWidth,
      pointRadius: Number(point?.getAttribute('r')),
    };
  });

  expect(layout.figureScrolls, 'the curve does not scroll sideways').toBe(false);
  expect(layout.chartWidth, 'the chart is as wide as its room').toBeLessThanOrEqual(
    layout.figureWidth,
  );
  expect(layout.pageWidth, 'the page does not scroll sideways').toBeLessThanOrEqual(PHONE.width);
  expect(layout.pointRadius, 'the points are smaller than with few').toBeLessThan(4);
});
