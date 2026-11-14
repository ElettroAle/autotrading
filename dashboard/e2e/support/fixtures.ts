import { createBdd, defineParameterType, test as base } from 'playwright-bdd';

import type { FakeCycle } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';

import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

/** What a scenario remembers between its steps. */
export type ScenarioMemory = {
  account: string;
  environments: string[];
  flow: string;
  cycles: FakeCycle[];
};

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
    await use({ account: '', environments: [], flow: '', cycles: [] });
  },
});

// A time of the day as the scenarios write it, 10:07:00.
defineParameterType({
  name: 'time',
  regexp: /\d{2}:\d{2}:\d{2}/,
  transformer: (time: string) => time,
});

export const { Given, When, Then } = createBdd(test);
