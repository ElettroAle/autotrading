import { createBdd, defineParameterType, test as base } from 'playwright-bdd';

import type { FakeCycle } from '@/testing/mocks/cycles';
import { fakePlatform, type FakeFlowHistory, type FakeVersion } from '@/testing/mocks/platform';

import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

/** A flow the background describes before the scenario names the user who owns it. */
export type DescribedFlow = { readonly name: string; readonly versions: FakeVersion[] };

/** What a scenario remembers between its steps: the histories wait for the user who owns their flow. */
export type ScenarioMemory = {
  account: string;
  tradingAccount: string;
  environments: string[];
  flow: string;
  cycles: FakeCycle[];
  histories: Map<string, FakeFlowHistory>;
  described: DescribedFlow | undefined;
  compared: number[];
  freeCapital: number | undefined;
  answerStatus: number | undefined;
  secondVersionFrom: number;
  /** The strategy file the user has, as text, and the flows of the user before an import (R2.5.2). */
  strategyFile: string;
  flowsBefore: string[];
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
    await use({
      account: '',
      tradingAccount: '',
      environments: [],
      flow: '',
      cycles: [],
      histories: new Map(),
      described: undefined,
      compared: [],
      freeCapital: undefined,
      answerStatus: undefined,
      secondVersionFrom: 1,
      strategyFile: '',
      flowsBefore: [],
    });
  },
});

// A time of the day as the scenarios write it, 10:07:00.
defineParameterType({
  name: 'time',
  regexp: /\d{2}:\d{2}:\d{2}/,
  transformer: (time: string) => time,
});

// An amount as the scenarios write it, in Italian with its sign (+12, 0,01), handed over as the API writes it (12, 0.01).
defineParameterType({
  name: 'amount',
  regexp: /[+-]?\d+(?:,\d+)?/,
  transformer: (amount: string) => amount.replace('+', '').replace(',', '.'),
});

// A percent as the dashboard shows it, +5,00%.
defineParameterType({
  name: 'percent',
  regexp: /[+-]?\d+(?:,\d+)?%/,
  transformer: (percent: string) => percent,
});

export const { Given, When, Then } = createBdd(test);
