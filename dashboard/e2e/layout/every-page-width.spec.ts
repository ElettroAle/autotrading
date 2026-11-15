import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { measurePages, preparePagesWithLongWords, signInOnTheFlows } from '../support/every-page';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const PHONE_WIDTH = 360;
const PHONE_HEIGHT = 780;

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR liste-etichetta-valore-che-vanno-a-capo: on a screen 360 pixels wide no page of the dashboard scrolls sideways
// and no element goes out of its box, even with names of models, accounts and errors that have no space to break.
test('ADR liste-etichetta-valore-che-vanno-a-capo: every page stays within a screen 360 pixels wide', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  await page.setViewportSize({ width: PHONE_WIDTH, height: PHONE_HEIGHT });
  const pages = preparePagesWithLongWords(ACCOUNT, 'prova-btc');
  await signInOnTheFlows(dashboard, ACCOUNT);

  const measured = await measurePages(dashboard, { ...pages, notFound: '/pagina-inesistente' });

  expect(measured.size).toBe(Object.keys(pages).length + 1);
  expect(Object.fromEntries([...measured].filter(([, spilled]) => spilled.length > 0))).toEqual({});
});
