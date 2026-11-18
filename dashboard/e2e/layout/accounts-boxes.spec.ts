import { expect, test, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';

import { DashboardPages } from '../support/dashboard-pages';
import { elementsOutOfTheirBox, overflowPastTheScreen } from '../support/every-page';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const ACCOUNTS = ['principale', 'conto-con-un-nome-molto-lungo-senza-spazi-per-andare-a-capo'];
const HEIGHT = 800;
const PHONE = 360;
const WIDE = 1280;

type Box = { readonly left: number; readonly top: number; readonly bottom: number };

const boxOf = async (box: Locator): Promise<Box> => {
  const { x, y, height } = (await box.boundingBox()) ?? { x: 0, y: 0, height: 0 };
  return { left: x, top: y, bottom: y + height };
};

const openTheAccounts = async (dashboard: DashboardPages, width: number): Promise<Box[]> => {
  await dashboard.page.setViewportSize({ width, height: HEIGHT });
  await dashboard.openAccounts();
  await dashboard.signInAs(ACCOUNT);
  for (const name of ACCOUNTS) {
    await expect(dashboard.accountReconciliationState(name)).toBeVisible();
  }
  await dashboard.waitUntilRead();
  return Promise.all(ACCOUNTS.map((name) => boxOf(dashboard.accountItem(name))));
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
  for (const name of ACCOUNTS) {
    fakePlatform.giveAccountTo(ACCOUNT, name, 1000);
  }
  fakeReconciliation.openAlarm(
    fakePlatform.accountNamed(ACCOUNTS[0] ?? '').id,
    1000,
    980,
    new Date(),
  );
});

// ADR conti-a-riquadri, Bug 565: on a phone the boxes of the accounts stand one below the other, and nothing of them
// goes past the screen or out of its box.
test(`ADR conti-a-riquadri: the boxes of the accounts stand one below the other within a screen ${PHONE} pixels wide`, async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  const [first, second] = await openTheAccounts(dashboard, PHONE);

  expect(second?.top, 'the second box starts below the first').toBeGreaterThanOrEqual(
    first?.bottom ?? Number.POSITIVE_INFINITY,
  );
  expect(await overflowPastTheScreen(dashboard), 'the page does not scroll sideways').toBe(0);
  expect(await elementsOutOfTheirBox(dashboard)).toEqual([]);
});

// ADR conti-a-riquadri, Bug 565: on a wide screen the boxes of the accounts stand side by side, two per row.
test(`ADR conti-a-riquadri: the boxes of the accounts stand side by side within a screen ${WIDE} pixels wide`, async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  const [first, second] = await openTheAccounts(dashboard, WIDE);

  expect(second?.top, 'the boxes start on the same row').toBe(first?.top);
  expect(second?.left, 'the second box stands beside the first').toBeGreaterThan(
    first?.left ?? Number.POSITIVE_INFINITY,
  );
  expect(await overflowPastTheScreen(dashboard), 'the page does not scroll sideways').toBe(0);
  expect(await elementsOutOfTheirBox(dashboard)).toEqual([]);
});
