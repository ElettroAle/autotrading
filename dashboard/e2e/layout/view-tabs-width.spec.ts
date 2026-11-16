import { expect, test, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { aStoppedFlow } from '../support/every-page';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const FLOW = 'prova-btc';
const PHONE_WIDTH = 360;
const PHONE_HEIGHT = 780;

type BarLayout = {
  readonly rows: number;
  readonly left: number;
  readonly right: number;
  readonly scrollsInside: boolean;
  readonly pageWidth: number;
};

const layoutOf = (bar: Locator): Promise<BarLayout> =>
  bar.evaluate((element) => {
    const tabs = [...element.querySelectorAll('a, [role="tab"]')];
    const box = element.getBoundingClientRect();
    return {
      rows: new Set(tabs.map((tab) => Math.round(tab.getBoundingClientRect().top))).size,
      left: box.left,
      right: box.right,
      scrollsInside: element.scrollWidth > element.clientWidth,
      pageWidth: document.documentElement.scrollWidth,
    };
  });

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR schede-con-aspetto-e-ruolo-di-schede: on a screen 360 pixels wide every bar of tabs stays on one row within the
// page, and the tabs that do not fit scroll inside the bar instead of pushing the page wider.
test('ADR schede-con-aspetto-e-ruolo-di-schede: every bar of tabs stays on one row within a screen 360 pixels wide', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  await page.setViewportSize({ width: PHONE_WIDTH, height: PHONE_HEIGHT });
  aStoppedFlow(ACCOUNT, FLOW);
  await dashboard.openFlowAs(ACCOUNT, FLOW);
  const bars = {
    flow: page.getByRole('navigation', { name: 'Dati del flusso' }),
    flows: page.getByRole('navigation', { name: 'Viste dei flussi' }),
    ranking: page.getByRole('navigation', { name: 'Viste dei flussi' }),
    history: page.getByRole('tablist', { name: 'Storici' }).locator('..'),
  };
  const opens = {
    flow: () => Promise.resolve(),
    flows: () => dashboard.open(),
    ranking: () => dashboard.openRanking(),
    history: () => dashboard.openHistory(),
  };

  const layouts: Record<string, BarLayout> = {};
  for (const [name, bar] of Object.entries(bars)) {
    await opens[name as keyof typeof opens]();
    await expect(bar).toBeVisible();
    layouts[name] = await layoutOf(bar);
  }

  for (const [name, layout] of Object.entries(layouts)) {
    expect(layout.rows, `${name}: the tabs on one row`).toBe(1);
    expect(layout.left, `${name}: the bar within the page`).toBeGreaterThanOrEqual(0);
    expect(layout.right, `${name}: the bar within the page`).toBeLessThanOrEqual(PHONE_WIDTH);
    expect(layout.pageWidth, `${name}: the page does not scroll sideways`).toBeLessThanOrEqual(
      PHONE_WIDTH,
    );
  }
  // A bar wider than the screen scrolls inside itself, never the page: on one row and within the page, its tabs that
  // do not fit can only scroll inside it. The three tabs of the flow fit at 360 pixels (R6.4.3).
  for (const [name, layout] of Object.entries(layouts)) {
    expect(
      layout.scrollsInside || layout.right <= PHONE_WIDTH,
      `${name}: fits or scrolls inside`,
    ).toBe(true);
  }
});
