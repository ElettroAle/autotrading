import { expect, test, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

// A name longer than the room a phone leaves it, so the bar is measured at its fullest.
const ACCOUNT = 'anna-maria-della-rovere';
const HEIGHT = 780;
const PHONES = [320, 360] as const;
const DESKTOP = 1280;
const DESKTOP_FROM = 768;
// A text kept only for screen readers is a single pixel wide.
const ONLY_FOR_SCREEN_READERS = 1;

type HeaderLayout = {
  readonly pageWidth: number;
  readonly headerBottom: number;
  readonly mainTop: number;
  readonly onOneLine: boolean;
  readonly outOfTheScreen: string[];
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

const openTheComparisonAt = async (dashboard: DashboardPages, width: number): Promise<void> => {
  fakePlatform.addUser(ACCOUNT, { hasUserRole: true });
  await dashboard.page.setViewportSize({ width, height: HEIGHT });
  await dashboard.openAndSignInAs(ACCOUNT);
  await dashboard.open('/comparison');
  await expect(dashboard.page.getByRole('button', { name: 'Indietro' })).toBeVisible();
};

const widthOf = async (text: Locator): Promise<number> => (await text.boundingBox())?.width ?? 0;

// What the bar holds, measured where it is: every element of the bar shares one line with the others and stays within
// the screen, and the content of the page starts below the bar.
const measureTheHeader = (dashboard: DashboardPages): Promise<HeaderLayout> =>
  dashboard.page.getByRole('banner').evaluate((header): HeaderLayout => {
    const items = [...header.querySelectorAll('button, a, [aria-label]')].filter(
      (item) => item.getBoundingClientRect().width > 0,
    );
    const boxes = items.map((item) => item.getBoundingClientRect());
    const lowestTop = Math.max(...boxes.map((box) => box.top));
    const highestBottom = Math.min(...boxes.map((box) => box.bottom));
    return {
      pageWidth: document.documentElement.scrollWidth,
      headerBottom: header.getBoundingClientRect().bottom,
      mainTop: document.querySelector('main')?.getBoundingClientRect().top ?? 0,
      onOneLine: lowestTop < highestBottom,
      outOfTheScreen: items
        .filter((item) => {
          const box = item.getBoundingClientRect();
          return box.left < 0 || box.right > window.innerWidth;
        })
        .map((item) => item.getAttribute('aria-label') ?? item.textContent ?? ''),
    };
  });

// Bug 592 and ADR intestazione-su-una-riga: on a phone from 320 pixels the bar on top stays on one line, its commands
// show only their icon and nothing goes out of the screen or under the bar.
for (const width of PHONES) {
  test(`ADR intestazione-su-una-riga, Bug 592: the bar on top stays on one line at ${width} pixels`, async ({
    page,
  }) => {
    const dashboard = new DashboardPages(page);
    await openTheComparisonAt(dashboard, width);
    const header = page.getByRole('banner');

    const layout = await measureTheHeader(dashboard);

    expect(layout.onOneLine, 'every element of the bar shares one line').toBe(true);
    expect(layout.outOfTheScreen).toEqual([]);
    expect(layout.pageWidth).toBeLessThanOrEqual(width);
    expect(layout.mainTop).toBeGreaterThanOrEqual(layout.headerBottom);
    await expect(header.getByRole('button', { name: 'Menu' })).toBeVisible();
    expect(await widthOf(header.getByText('Indietro'))).toBeLessThanOrEqual(
      ONLY_FOR_SCREEN_READERS,
    );
    expect(await widthOf(header.getByText(ACCOUNT))).toBeLessThanOrEqual(ONLY_FOR_SCREEN_READERS);
    await expect(header.getByLabel("Ambiente dell'installazione")).toBeVisible();
    await expect(header.locator('[data-icon="chevron-down"]')).toBeHidden();
  });
}

// ADR intestazione-su-una-riga: from 768 pixels the bar shows the words of its commands and the name of the user.
test(`ADR intestazione-su-una-riga: the bar on top shows «Indietro» and the name of the user from ${DESKTOP_FROM} pixels`, async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  await openTheComparisonAt(dashboard, DESKTOP);
  const header = page.getByRole('banner');

  const layout = await measureTheHeader(dashboard);

  expect(layout.onOneLine).toBe(true);
  expect(await widthOf(header.getByText('Indietro'))).toBeGreaterThan(ONLY_FOR_SCREEN_READERS);
  expect(await widthOf(header.getByText(ACCOUNT))).toBeGreaterThan(ONLY_FOR_SCREEN_READERS);
  await expect(header.locator('[data-icon="chevron-down"]')).toBeVisible();
});
