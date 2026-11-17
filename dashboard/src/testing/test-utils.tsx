import {
  loadExternalTokens,
  type INavigationClient,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import { render, screen, within, type ByRoleMatcher } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createMemoryRouter } from 'react-router';

import { App } from '@/app';
import { routes } from '@/app/router';
import type { RuntimeConfig } from '@/config/runtime-config';
import { authConfiguration, completeSignIn, createAuthClient } from '@/lib/auth';

import { FAKE_IDENTITY_PROVIDER, tokenResponseOf } from './mocks/identity-provider';

export const TEST_CONFIG: RuntimeConfig = { environment: 'dev', ...FAKE_IDENTITY_PROVIDER };

export const TEST_REDIRECT_URI = 'http://localhost:3000/dashboard/';

// jsdom cannot leave the page: a redirect to the identity provider stays where it is, as one the browser blocked.
const stayingNavigation: INavigationClient = {
  navigateInternal: () => Promise.resolve(false),
  navigateExternal: () => Promise.resolve(false),
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
