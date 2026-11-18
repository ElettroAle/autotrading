import {
  loadExternalTokens,
  PublicClientApplication,
  type INavigationClient,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
  type ByRoleMatcher,
} from '@testing-library/react';
import type { ReactNode } from 'react';
import { createMemoryRouter } from 'react-router';

import { App } from '@/app';
import { routes } from '@/app/router';
import type { RuntimeConfig } from '@/config/runtime-config';
import { authConfiguration, completeSignIn, createAuthClient } from '@/lib/auth';

import { FAKE_IDENTITY_PROVIDER, tokenResponseOf } from './mocks/identity-provider';
import { fakePlatform } from './mocks/platform';
import { server } from './mocks/server';

export const TEST_CONFIG: RuntimeConfig = { environment: 'dev', ...FAKE_IDENTITY_PROVIDER };

export const TEST_REDIRECT_URI = 'http://localhost:3000/dashboard/';

// jsdom cannot leave the page: a redirect to the identity provider stays where it is, as one the browser blocked.
const stayingNavigation: INavigationClient = {
  navigateInternal: () => Promise.resolve(false),
  navigateExternal: () => Promise.resolve(false),
};

const redirectOfMsal = PublicClientApplication.prototype.acquireTokenRedirect;

// A redirect leaves the page, so in the browser its promise never settles: one that settled in jsdom could do it after
// the end of the test, on a closed jsdom (ADR redirect-dell-accesso-che-non-torna-nei-test). A test that wants another
// redirect says so with its own spy, on the client or on every client of MSAL.
const leavingThePageFor =
  (client: IPublicClientApplication): IPublicClientApplication['acquireTokenRedirect'] =>
  (request) => {
    const redirectOfEveryClient = PublicClientApplication.prototype.acquireTokenRedirect;
    if (redirectOfEveryClient !== redirectOfMsal) {
      return redirectOfEveryClient.call(client, request);
    }
    return new Promise<void>(() => undefined);
  };

/** A client of the fake identity provider, with the account already signed in when one is given. */
export const authClientFor = async (account?: string): Promise<IPublicClientApplication> => {
  if (account !== undefined) {
    await loadExternalTokens(
      authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI),
      { scopes: [FAKE_IDENTITY_PROVIDER.scope], authority: FAKE_IDENTITY_PROVIDER.issuer },
      tokenResponseOf(account),
      {},
    );
  }
  const client = createAuthClient(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI);
  client.setNavigationClient(stayingNavigation);
  client.acquireTokenRedirect = leavingThePageFor(client);
  await completeSignIn(client);
  return client;
};

/** The whole dashboard at a page, as a user with the account (or a visitor) opens it. */
export const renderApp = async ({
  account,
  url = '/',
}: { account?: string; url?: string } = {}) => {
  const authClient = await authClientFor(account);
  const router = createMemoryRouter(routes, { initialEntries: [url] });
  render(<App config={TEST_CONFIG} authClient={authClient} router={router} />);
  return { router, authClient };
};

/** A piece of the dashboard alone, inside the providers of the dashboard, as a user with the account sees it. */
export const renderInApp = async (ui: ReactNode, { account }: { account?: string } = {}) => {
  const authClient = await authClientFor(account);
  const router = createMemoryRouter([{ path: '*', element: ui }]);
  render(<App config={TEST_CONFIG} authClient={authClient} router={router} />);
};

export const WARM_UP_ACCOUNT = 'warm-up';

const WARM_UP_FLOW = 'riscaldamento';

// Measured with Vitest on 4 processors (Bug 610): the first opening of the dashboard in a file takes about 800 ms against
// 300 ms for the next ones, the code of MSAL, MSW, React and the pages still cold. Under a load of two workers per
// processor it lasts seconds, so it gets the time of a fixed cost here, never in a test.
const WARM_UP_TIMEOUT_MS = 60_000;

const pendingRequests = new Set<string>();

server.events.on('request:start', ({ requestId }) => pendingRequests.add(requestId));
server.events.on('request:end', ({ requestId }) => pendingRequests.delete(requestId));

/** Opens the dashboard of a user with a flow, until the list shows it and the API has answered every reading. */
const openTheDashboardOnce = async (): Promise<void> => {
  fakePlatform.addUser(WARM_UP_ACCOUNT, { hasUserRole: true });
  fakePlatform.addFlow(WARM_UP_ACCOUNT, WARM_UP_FLOW);
  await renderApp({ account: WARM_UP_ACCOUNT });
  await screen.findByRole('link', { name: WARM_UP_FLOW }, { timeout: WARM_UP_TIMEOUT_MS });
  await waitFor(() => expect(pendingRequests).toHaveLength(0), { timeout: WARM_UP_TIMEOUT_MS });
};

/** The first test finds what every test finds: no page, an empty platform, a browser that holds nothing. */
const forgetTheOpening = (): void => {
  cleanup();
  fakePlatform.reset();
  sessionStorage.clear();
  localStorage.clear();
};

// The first test of a file would pay the first opening of the dashboard on its own clock (ADR
// test-della-dashboard-deterministici): every file that renders the dashboard opens it once before its tests.
beforeAll(async () => {
  await openTheDashboardOnce();
  forgetTheOpening();
}, WARM_UP_TIMEOUT_MS);

// What a user sees as a part of a page: its commands, its links, its titles, its tables, its lists and its boxes.
const PARTS_OF_A_PAGE: readonly ByRoleMatcher[] = [
  'button',
  'link',
  'heading',
  'table',
  'list',
  'region',
  'group',
  'form',
  'alertdialog',
];

const isWithinOrBefore = (part: HTMLElement, box: HTMLElement): boolean =>
  part === box ||
  box.contains(part) ||
  (part.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;

/**
 * The parts of the content of the page that come after the box, outside it: none when the box is at the bottom of the
 * page (ADR zona-di-emergenza-in-fondo-alla-pagina).
 */
export const partsAfter = (box: HTMLElement): HTMLElement[] => {
  const content = screen.getByRole('main');
  return PARTS_OF_A_PAGE.flatMap((role) => within(content).queryAllByRole(role)).filter(
    (part) => !isWithinOrBefore(part, box),
  );
};
