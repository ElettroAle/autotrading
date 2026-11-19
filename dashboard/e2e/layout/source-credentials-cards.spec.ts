import { expect, test } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeSourceCredentials } from '@/testing/mocks/source-credentials';

import { DashboardPages } from '../support/dashboard-pages';
import { routeToFakes } from '../support/fake-network';

const ACCOUNT = 'anna';
const HEIGHT = 800;
const PHONE = 360;
const DESKTOP = 1280;
const ADAPTER = 'LunarCrush';

type SectionLayout = {
  readonly pageWidth: number;
  readonly commandsOutOfTheirCard: string[];
  readonly commandsBelowTheText: boolean;
};

test.beforeEach(async ({ page, baseURL }) => {
  fakePlatform.reset();
  await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
});

// ADR sezione-fonti-nella-pagina-chiavi: under 640 pixels each adapter is a card with its commands below its text, no
// horizontal scrolling; on a wide screen the commands sit beside the text.
for (const width of [PHONE, DESKTOP]) {
  test(`ADR sezione-fonti-nella-pagina-chiavi: each adapter of the sources is a card that holds its commands at ${width} pixels`, async ({
    page,
  }) => {
    const dashboard = new DashboardPages(page);
    fakePlatform.addUser(ACCOUNT, { hasUserRole: true });
    fakeSourceCredentials.offerAdapter('sentiment', ADAPTER);
    fakeSourceCredentials.configure(ACCOUNT, ADAPTER, { api_key: 'K' }, '2026-11-14T09:00:00Z');
    await page.setViewportSize({ width, height: HEIGHT });
    await dashboard.openAndSignInAs(ACCOUNT);
    await dashboard.open('/provider-keys');
    const card = page
      .getByRole('region', { name: 'Fonti' })
      .getByRole('listitem', { name: ADAPTER });
    await expect(card.getByRole('button', { name: 'Rimuovi' })).toBeVisible();

    const layout = await card.evaluate((element): SectionLayout => {
      const box = element.getBoundingClientRect();
      const buttons = [...element.querySelectorAll('button')];
      const outside = buttons
        .filter((button) => {
          const own = button.getBoundingClientRect();
          return own.left < box.left || own.right > box.right;
        })
        .map((button) => button.textContent ?? '');
      // The text of the card: the name of the adapter, its state, its values and its expiry.
      const name = element.firstElementChild?.firstElementChild?.getBoundingClientRect();
      const first = buttons[0]?.getBoundingClientRect();
      return {
        pageWidth: document.documentElement.scrollWidth,
        commandsOutOfTheirCard: outside,
        commandsBelowTheText: name !== undefined && first !== undefined && first.top >= name.bottom,
      };
    });

    expect(layout.commandsOutOfTheirCard).toEqual([]);
    expect(layout.pageWidth).toBeLessThanOrEqual(width);
    expect(layout.commandsBelowTheText).toBe(width === PHONE);
  });
}
