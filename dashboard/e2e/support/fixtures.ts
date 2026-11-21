import { createBdd, defineParameterType, test as base } from 'playwright-bdd';

import type { FakeSource, FakeSourceParameter } from '@/testing/mocks/catalogs';
import type { FakeCycle } from '@/testing/mocks/cycles';
import {
  fakePlatform,
  type FakeEquityPoint,
  type FakeFlowHistory,
  type FakeVersion,
} from '@/testing/mocks/platform';
import type { FakeSourceTrial } from '@/testing/mocks/source-trials';

import { BrowserRestart } from './browser-restart';
import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

/** A flow the background describes before the scenario names the user who owns it. */
export type DescribedFlow = { readonly name: string; readonly versions: FakeVersion[] };

/**
 * What a scenario remembers between its steps: the histories wait for the user who owns their flow, the secret typed
 * in a form is looked for in the pages, the account or key acted on is named once, the instant a key was registered is
 * compared with the next one.
 */
export type ScenarioMemory = {
  account: string;
  /** The user the background gave its flows to, for the flows a later step adds (R6.4.6). */
  owner: string;
  tradingAccount: string;
  environments: string[];
  flow: string;
  cycles: FakeCycle[];
  /** The cycle the user chose, whose detail the page should show. */
  chosenCycle: FakeCycle | undefined;
  histories: Map<string, FakeFlowHistory>;
  /** The equity the cycles of a flow recorded, by the name of the flow, waiting for the flow like its history (R2.2.6). */
  equities: Map<string, FakeEquityPoint[]>;
  described: DescribedFlow | undefined;
  compared: number[];
  freeCapital: number | undefined;
  answerStatus: number | undefined;
  secondVersionFrom: number;
  /** The strategy file the user has, as text, and the flows of the user before an import (R2.5.2). */
  strategyFile: string;
  flowsBefore: string[];
  secret: string;
  subject: string;
  registeredAt: string;
  /** The reason the refusal a step caused is expected to give. */
  refusal: string;
  /** The page whose period the user chooses, when it is not the page of the flow (R2.4.2). */
  periodPage: string;
  /** The time a new cycle of the flow concluded, as the page should show it (R2.1.2). */
  newCycleAt: string;
  /** The instant of the change of capital the history should show, as the API answers it (R3.4.2). */
  capitalChangedAt: string;
  /** What spilled past the screen on each page the user opened, by the name of the page (R6.4.1). */
  spilledByPage: Map<string, string[]>;
  /** The widths of the screens the pages are opened on, one after the other (R6.4.4). */
  screenWidths: number[];
  /** How many times the identity provider had asked the credentials before the step that must not ask them (R6.5.1). */
  credentialPages: number;
  /** How many times the browser had gone to the identity provider before the session was renewed (R6.5.1). */
  signInRedirects: number;
  /** The headers and the page the dashboard answered when the browser loaded it (R6.5.1). */
  loadedPage: { readonly headers: Record<string, string>; readonly body: string } | undefined;
  /** What the browser blocked under the content security policy of the dashboard (R6.5.1). */
  policyViolations: string[];
  /** The sources and their adapters as the API listed them to the editor of the flow (R4.1.1). */
  sourceCatalog: FakeSource[];
  /** The parameter of an adapter the user set to a value it does not admit (R4.1.1). */
  sourceParameter: FakeSourceParameter | undefined;
  /** The last trial of a source the API answered, whose outcome the page should show (R6.3.1). */
  sourceTrial: FakeSourceTrial | undefined;
};

type Fixtures = {
  fakes: void;
  dashboard: DashboardPages;
  memory: ScenarioMemory;
  browserRestart: BrowserRestart;
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
  browserRestart: async ({ page, browser, baseURL, timezoneId }, use) => {
    const restart = new BrowserRestart(page, browser, { baseURL, timezoneId });
    await use(restart);
    await restart.dispose();
  },
  memory: async ({}, use) => {
    await use({
      account: '',
      owner: '',
      tradingAccount: '',
      environments: [],
      flow: '',
      cycles: [],
      chosenCycle: undefined,
      histories: new Map(),
      equities: new Map(),
      described: undefined,
      compared: [],
      freeCapital: undefined,
      answerStatus: undefined,
      secondVersionFrom: 1,
      strategyFile: '',
      flowsBefore: [],
      secret: '',
      subject: '',
      registeredAt: '',
      refusal: '',
      periodPage: '',
      newCycleAt: '',
      capitalChangedAt: '',
      spilledByPage: new Map(),
      screenWidths: [],
      credentialPages: 0,
      signInRedirects: 0,
      loadedPage: undefined,
      policyViolations: [],
      sourceCatalog: [],
      sourceParameter: undefined,
      sourceTrial: undefined,
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
