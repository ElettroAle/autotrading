import { createBdd, test as base } from 'playwright-bdd';

import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

/** What a scenario remembers between its steps. */
export type ScenarioMemory = { account: string; environments: string[] };

type Fixtures = {
  fakes: void;
  dashboard: DashboardPages;
  memory: ScenarioMemory;
};

export const test = base.extend<Fixtures>({
  // Every scenario starts from an empty platform, with the browser routed to the fakes and a clock it can move.
  fakes: [
    async ({ page, baseURL }, use) => {
      fakePlatform.reset();
      await page.clock.install();
      await routeToFakes(page, new URL(baseURL ?? 'http://127.0.0.1').origin);
      await use();
    },
    { auto: true },
  ],
  dashboard: async ({ page }, use) => {
    await use(new DashboardPages(page));
  },
  memory: async ({}, use) => {
    await use({ account: '', environments: [] });
  },
});

export const { Given, When, Then } = createBdd(test);
