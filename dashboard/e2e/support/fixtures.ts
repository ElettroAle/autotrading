import { createBdd, defineParameterType, test as base } from 'playwright-bdd';

import type { FakeCycle } from '@/testing/mocks/cycles';
import { fakePlatform, type FakeFlowHistory } from '@/testing/mocks/platform';

import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

/** What a scenario remembers between its steps: the histories wait for the user who owns their flow. */
export type ScenarioMemory = {
  account: string;
  environments: string[];
  flow: string;
  cycles: FakeCycle[];
  histories: Map<string, FakeFlowHistory>;
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
    await use({ account: '', environments: [], flow: '', cycles: [], histories: new Map() });
  },
});

// A time of the day as the scenarios write it, 10:07:00.
defineParameterType({
  name: 'time',
  regexp: /\d{2}:\d{2}:\d{2}/,
  transformer: (time: string) => time,
});

export const { Given, When, Then } = createBdd(test);
