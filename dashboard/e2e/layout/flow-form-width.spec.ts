import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR 0146: on a phone no field of the form of the flow goes past the width of the page, whatever the catalog names.
test('ADR 0146: every field of the form of a new flow stays within the width of a phone', async ({
  page,
}) => {
  const dashboard = new DashboardPages(page);
  fakePlatform.addUser(ACCOUNT, { hasUserRole: true });
  fakePlatform.giveAccountTo(ACCOUNT, 'principale', 500);
  await dashboard.openAndSignInAs(ACCOUNT);
  await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
  await dashboard.openNewFlow();
  const form = page.getByRole('form', { name: 'Configurazione del flusso' });
  await expect(dashboard.field('Modello')).toBeVisible();
  await page.getByRole('checkbox', { name: 'indicatori', exact: true }).check();
  await expect(dashboard.field('Peso di indicatori')).toBeVisible();

  const width = page.viewportSize()?.width ?? 0;
  const overflowing = await form
    .locator('input, select, textarea, button, [role="combobox"]')
    .evaluateAll(
      (fields, pageWidth) =>
        fields
          .filter((field) => field.getBoundingClientRect().right > pageWidth)
          .map((field) => field.getAttribute('aria-label') ?? field.id),
      width,
    );
  expect(overflowing).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    width,
  );
});
