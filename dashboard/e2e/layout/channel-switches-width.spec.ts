import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const HEIGHT = 800;
const PHONE = 360;
const DESKTOP = 1280;
const GENERAL = 'Canali per tipo di evento';

type SwitchesLayout = {
  readonly pageWidth: number;
  readonly switchesOutOfTheirCell: string[];
  readonly rowsAsCards: boolean;
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR interruttori-dei-canali-nelle-preferenze: the switches of the channels stay in the row of their event and wrap
// inside it, on a phone 360 pixels wide (a card per event) as on a screen 1280 pixels wide (a table).
for (const width of [PHONE, DESKTOP]) {
  test(`ADR interruttori-dei-canali-nelle-preferenze: the switches of the channels stay in the row of their event at ${width} pixels`, async ({
    page,
  }) => {
    const dashboard = new DashboardPages(page);
    fakePlatform.addUser(ACCOUNT, { hasUserRole: true });
    fakePlatform.linkChat(ACCOUNT, 'chat-anna');
    await page.setViewportSize({ width, height: HEIGHT });
    await dashboard.openAndSignInAs(ACCOUNT);
    await dashboard.open('/notifications?tab=preferences');
    const table = page.getByRole('table', { name: GENERAL });
    await expect(table.getByRole('button', { name: 'Telegram' }).first()).toBeVisible();

    const layout = await table.evaluate((element): SwitchesLayout => {
      const groups = [...element.querySelectorAll('[role="group"]')];
      const outside = groups.flatMap((group) => {
        const cell = group.closest('td')?.getBoundingClientRect();
        return [...group.querySelectorAll('button')]
          .filter((button) => {
            const box = button.getBoundingClientRect();
            return cell === undefined || box.left < cell.left || box.right > cell.right;
          })
          .map(
            (button) => `${group.getAttribute('aria-label') ?? ''}: ${button.textContent ?? ''}`,
          );
      });
      const firstRow = element.querySelector('tbody tr');
      return {
        pageWidth: document.documentElement.scrollWidth,
        switchesOutOfTheirCell: outside,
        rowsAsCards: firstRow !== null && getComputedStyle(firstRow).display === 'block',
      };
    });

    expect(layout.switchesOutOfTheirCell).toEqual([]);
    expect(layout.pageWidth).toBeLessThanOrEqual(width);
    expect(layout.rowsAsCards).toBe(width === PHONE);
  });
}
