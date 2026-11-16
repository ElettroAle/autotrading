import { expect } from '@playwright/test';

import { paths } from '@/config/paths';
import { aCompletedCycle, aFailedCycle, apiInstant, STEPS } from '@/testing/mocks/cycles';
import {
  aHistoryCycle,
  aHistoryOrder,
  aHistoryPosition,
  anExecution,
} from '@/testing/mocks/history';
import { fakePlatform, versionsWith, type FakeFlow } from '@/testing/mocks/platform';
import { aClosedPosition, anOpenPosition } from '@/testing/mocks/positions';

import type { DashboardPages } from './dashboard-pages';

/** A name of a model with no space to break it, as the catalogs of the providers have (R6.4.1). */
export const LONG_MODEL = 'openrouter/~deepseek/deepseek-flash-latest';

// Every value the pages show is as long as the platform allows, with no space to break it.
const LONG_ACCOUNT = 'conto-principale-della-piattaforma-di-prova';
const LONG_FAILURE =
  'ModelCallTimeoutError:openrouter/~deepseek/deepseek-flash-latest/non-ha-risposto-entro-60-secondi';
const LONG_PROVIDER = 'openrouter-con-un-nome-di-fornitore-molto-lungo';
const DAY = Date.UTC(2026, 10, 14, 9, 0);
const HOUR = 3_600_000;

/** A stopped flow of the user, as the scenarios of R6.4.1 describe it: Avvia and Archivia are its commands. */
export const aStoppedFlow = (account: string, name: string, model = 'openai/gpt-4o'): FakeFlow => {
  fakePlatform.ensureUser(account);
  return fakePlatform.addFlow(account, name, {
    status: 'fermo',
    model,
    accountName: LONG_ACCOUNT,
    versions: versionsWith({}, { model }),
  });
};

/** The data behind every page of the dashboard, each value with long words, and the address of every page. */
export const preparePagesWithLongWords = (
  account: string,
  flowName: string,
): Record<keyof typeof paths, string> => {
  const flow = aStoppedFlow(account, flowName, LONG_MODEL);
  flow.sources = [{ name: 'indicatori', weight: 1 }];
  const completed = aCompletedCycle(new Date(DAY));
  const failed = aFailedCycle(aCompletedCycle(new Date(DAY - HOUR)), STEPS.agentDecision, {
    errorType: 'ModelCallTimeoutError',
    message: LONG_FAILURE,
  });
  fakePlatform.recordCycles(flowName, [completed, failed]);
  fakePlatform.recordEquity(flowName, new Date(DAY - HOUR), 100);
  fakePlatform.recordEquity(flowName, new Date(DAY), 104);
  fakePlatform.holdPositions(flowName, [anOpenPosition()]);
  fakePlatform.recordClosedPositions(flowName, [
    aClosedPosition({ closedAt: new Date(DAY), reason: LONG_FAILURE }),
  ]);
  fakePlatform.saveProviderKey(account, LONG_PROVIDER, apiInstant(new Date(DAY)));
  const owner = {
    flowId: flow.id,
    flow: flow.name,
    accountId: flow.accountId ?? '',
    account: LONG_ACCOUNT,
    version: flow.version,
  };
  const records = fakePlatform.recordsOf(account);
  records.cycles.push(aHistoryCycle(owner, new Date(DAY), ['BTC']));
  records.closedPositions.push(aHistoryPosition(owner, 'BTC', new Date(DAY)));
  records.orders.push(
    aHistoryOrder(owner, 'BTC', new Date(DAY), [
      anExecution(new Date(DAY), '60000', '0.001', '0.01'),
    ]),
  );
  return {
    home: paths.home.getHref(),
    login: paths.login.getHref(),
    accounts: paths.accounts.getHref(),
    newFlow: paths.newFlow.getHref(),
    flow: paths.flow.getHref(flow.id),
    editFlow: paths.editFlow.getHref(flow.id),
    notifications: paths.notifications.getHref(),
    history: paths.history.getHref(),
    providerKeys: paths.providerKeys.getHref(),
    flowCycles: paths.flowCycles.getHref(flow.id),
    flowPositions: paths.flowPositions.getHref(flow.id),
    flowClosedPositions: paths.flowClosedPositions.getHref(flow.id),
    cycle: paths.cycle.getHref(flow.id, failed.planned_at),
    flowVersions: paths.flowVersions.getHref(flow.id),
    ranking: paths.ranking.getHref(),
    comparison: paths.comparison.getHref([flow.id]),
  };
};

/**
 * The elements of the page that go past the screen or out of their own box, by tag and text: a text wider than its
 * box spills over its neighbours even when the page does not scroll. Fields cut their value short on purpose
 * (ADR 0146), boxes that scroll their content keep it inside, and the text for screen readers is hidden on purpose. A
 * chart as wide as its room is measured through a box of no size on purpose, so it can shrink: its own width within its
 * room is proven by e2e/layout/equity-curve-width.spec.ts (ADR equity-curve-larga-come-lo-schermo).
 */
export const elementsOutOfTheirBox = async (dashboard: DashboardPages): Promise<string[]> =>
  dashboard.page.evaluate((width) => {
    const scrolls = (element: Element): boolean =>
      element !== document.body &&
      element !== document.documentElement &&
      getComputedStyle(element).overflowX !== 'visible';
    const insideAScrollingBox = (element: HTMLElement): boolean => {
      for (let box: Element | null = element; box !== null; box = box.parentElement) {
        if (scrolls(box)) {
          return true;
        }
      }
      return false;
    };
    const exempt = (element: HTMLElement): boolean =>
      element.closest('input, select, textarea, .sr-only, svg, .recharts-responsive-container') !==
        null ||
      getComputedStyle(element).display === 'contents' ||
      insideAScrollingBox(element);
    return [...document.body.querySelectorAll<HTMLElement>('*')]
      .filter((element) => element instanceof HTMLElement && !exempt(element))
      .filter((element) => {
        const box = element.getBoundingClientRect();
        const pastTheScreen = box.width > 0 && (box.left < -0.5 || box.right > width + 0.5);
        return pastTheScreen || element.scrollWidth > element.clientWidth + 1;
      })
      .map((element) => `${element.tagName}: ${(element.textContent ?? '').slice(0, 60)}`);
  }, screenWidth(dashboard));

// A phone widens the page to what it holds: the width of the screen is the one the test chose, not the page's.
const screenWidth = (dashboard: DashboardPages): number =>
  dashboard.page.viewportSize()?.width ?? 0;

/** How far the page reaches beyond the width of the screen: what the user would have to scroll sideways. */
export const overflowPastTheScreen = async (dashboard: DashboardPages): Promise<number> =>
  (await dashboard.page.evaluate(() => document.documentElement.scrollWidth)) -
  screenWidth(dashboard);

const BASE_PATH = '/dashboard';

const pathOf = (address: string): string => new URL(address, 'http://dashboard.test').pathname;

/** Signs in on the first page, the list of the flows, so the next pages open already signed in. */
export const signInOnTheFlows = async (
  dashboard: DashboardPages,
  account: string,
): Promise<void> => {
  await dashboard.openAndSignInAs(account);
  await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
};

/** How far each page goes past the screen and what spills out of its box, once the page has read its data. */
export const measurePages = async (
  dashboard: DashboardPages,
  pages: Record<string, string>,
): Promise<Map<string, string[]>> => {
  const measured = new Map<string, string[]>();
  for (const [name, path] of Object.entries(pages)) {
    await dashboard.open(path);
    // A page that sent the user to sign in would measure the sign-in page instead of itself.
    await expect(dashboard.page).toHaveURL((url) => url.pathname === `${BASE_PATH}${pathOf(path)}`);
    await expect(dashboard.pageHeading()).toBeVisible();
    await dashboard.waitUntilRead();
    const overflow = await overflowPastTheScreen(dashboard);
    const spilled = await elementsOutOfTheirBox(dashboard);
    measured.set(
      name,
      overflow > 0 ? [`pagina larga ${overflow} pixel oltre lo schermo`, ...spilled] : spilled,
    );
  }
  return measured;
};
