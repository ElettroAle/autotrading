import { expect, test, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { aStoppedFlow } from '../support/every-page';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const FLOW = 'prova-btc';
const TABS = ['Panoramica', 'Posizioni chiuse', 'Cicli'] as const;
const NARROW_BAR = 200;
const SCREENS = [
  { width: 360, height: 780 },
  { width: 1280, height: 800 },
] as const;

type BarLayout = {
  readonly scrollerLeft: number;
  readonly scrollerRight: number;
  readonly firstTabLeft: number;
  readonly firstTabRight: number;
  readonly backgroundLeft: number;
  readonly backgroundRight: number;
  readonly tabsLeft: number;
  readonly tabsRight: number;
  readonly pageWidth: number;
  readonly scrolls: boolean;
};

// The bar measured from its first scroll position: the scroller, the background of the tabs and the tabs themselves,
// the background as wide as the box it paints.
const layoutOf = (bar: Locator): Promise<BarLayout> =>
  bar.evaluate((scroller) => {
    const background = scroller.firstElementChild;
    const tabs = [...scroller.querySelectorAll('a, [role="tab"]')].map((tab) =>
      tab.getBoundingClientRect(),
    );
    const box = scroller.getBoundingClientRect();
    const backgroundBox = background?.getBoundingClientRect() ?? box;
    return {
      scrollerLeft: box.left,
      scrollerRight: box.right,
      firstTabLeft: tabs[0]?.left ?? 0,
      firstTabRight: tabs[0]?.right ?? 0,
      backgroundLeft: backgroundBox.left,
      backgroundRight: backgroundBox.right,
      tabsLeft: Math.min(...tabs.map((tab) => tab.left)),
      tabsRight: Math.max(...tabs.map((tab) => tab.right)),
      pageWidth: document.documentElement.scrollWidth,
      scrolls: scroller.scrollWidth > scroller.clientWidth,
    };
  });

const expectWholeBar = (layout: BarLayout, where: string, width: number): void => {
  expect(
    layout.firstTabLeft,
    `${where}: the first tab starts within the bar`,
  ).toBeGreaterThanOrEqual(layout.scrollerLeft);
  expect(layout.firstTabRight, `${where}: the first tab ends within the bar`).toBeLessThanOrEqual(
    layout.scrollerRight,
  );
  expect(
    layout.backgroundLeft,
    `${where}: the background starts before the tabs`,
  ).toBeLessThanOrEqual(layout.tabsLeft);
  expect(
    layout.backgroundRight,
    `${where}: the background reaches past the last tab`,
  ).toBeGreaterThanOrEqual(layout.tabsRight);
  expect(layout.pageWidth, `${where}: the page does not scroll sideways`).toBeLessThanOrEqual(
    width,
  );
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// Bug 439 and ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune: on a phone and on a wide screen the bar of the
// flow shows its first tab in full, its background covers every tab even where it scrolls, and it stays above the
// content of every tab.
for (const screen of SCREENS) {
  test(`ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, Bug 439: the bar of the flow shows every tab on its background, ${screen.width} pixels wide`, async ({
    page,
  }) => {
    const dashboard = new DashboardPages(page);
    await page.setViewportSize(screen);
    aStoppedFlow(ACCOUNT, FLOW);
    await dashboard.openFlowAs(ACCOUNT, FLOW);
    const bar = page.getByRole('navigation', { name: 'Dati del flusso' });

    for (const tab of TABS) {
      await bar.getByRole('link', { name: tab }).click();
      await expect(bar.getByRole('link', { name: tab })).toHaveAttribute('aria-current', 'page');
      await expect(bar).toBeInViewport();
      expectWholeBar(await layoutOf(bar), tab, screen.width);
      await bar.evaluate((scroller) => {
        scroller.scrollLeft = 0;
      });
    }
  });
}

// Bug 439: where its tabs do not fit, the bar scrolls from its first tab, with its background under all of them. The
// three tabs of the flow fit a phone, so the bar is given less room than its tabs, as on a narrower screen.
test('Bug 439: a bar of tabs that scrolls starts from its first tab and has its background under every tab', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  const [phone] = SCREENS;
  await page.setViewportSize(phone);
  aStoppedFlow(ACCOUNT, FLOW);
  await dashboard.openFlowAs(ACCOUNT, FLOW);
  const bar = page.getByRole('navigation', { name: 'Dati del flusso' });
  await bar.evaluate((scroller, width) => {
    scroller.style.maxWidth = `${width}px`;
  }, NARROW_BAR);
  const layout = await layoutOf(bar);

  expect(layout.scrolls, 'the tabs do not fit the bar').toBe(true);
  expectWholeBar(layout, 'narrow bar', phone.width);
});
