import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { measurePages, preparePagesWithLongWords, signInOnTheFlows } from '../support/every-page';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
// A phone, and a screen wide enough for the table view but narrower than the widest tables.
const WIDTHS = [360, 900];
const HEIGHT = 800;

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR tabella-condivisa-senza-sforamento-e-con-filtri: no table widens the page. Under 768 pixels the rows are cards;
// above, a table wider than the screen scrolls inside its own box with the first column fixed.
test('ADR tabella-condivisa-senza-sforamento-e-con-filtri: the tables stay within screens 360 and 900 pixels wide', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  const pages = preparePagesWithLongWords(ACCOUNT, 'prova-btc');
  await signInOnTheFlows(dashboard, ACCOUNT);
  const tables = {
    closedPositions: pages.flowClosedPositions,
    cycles: pages.flowCycles,
    ranking: pages.ranking,
    history: pages.history,
  };
  const spilled: Record<string, string[]> = {};

  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: HEIGHT });
    const measured = await measurePages(dashboard, tables);
    measured.forEach((elements, name) => {
      spilled[`${name} a ${width}`] = elements;
    });
  }

  expect(Object.keys(spilled)).toHaveLength(Object.keys(tables).length * WIDTHS.length);
  expect(
    Object.fromEntries(Object.entries(spilled).filter(([, elements]) => elements.length > 0)),
  ).toEqual({});
});

test('ADR tabella-condivisa-senza-sforamento-e-con-filtri: a table wider than the screen scrolls inside its box with the first column fixed', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  const pages = preparePagesWithLongWords(ACCOUNT, 'prova-btc');
  await signInOnTheFlows(dashboard, ACCOUNT);
  await page.setViewportSize({ width: 900, height: HEIGHT });
  await dashboard.open(pages.flowClosedPositions);
  await dashboard.waitUntilRead();

  const box = page.getByRole('region', { name: 'Posizioni chiuse' });
  const overflow = await box.evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(overflow).toBeGreaterThan(0);
  const first = dashboard.closedPositionRows().first().locator('td').first();
  const before = await first.boundingBox();
  await box.evaluate((element, left) => element.scrollBy({ left }), overflow);
  await expect.poll(() => box.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
  const after = await first.boundingBox();
  expect(after?.x).toBe(before?.x);
});
