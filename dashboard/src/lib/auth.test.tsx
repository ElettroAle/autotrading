import { BrowserCacheLocation } from '@azure/msal-browser';
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { accessTokenOf, fakePlatform } from '@/testing/mocks/platform';
import { authClientFor, TEST_REDIRECT_URI } from '@/testing/test-utils';

import {
  acquireAccessToken,
  authConfiguration,
  AuthProvider,
  completeSignIn,
  ProtectedRoute,
  returnPathOf,
  SessionExpiredError,
} from './auth';

const SCOPE = FAKE_IDENTITY_PROVIDER.scope;

describe('authConfiguration', () => {
  // ADR-0118: tokens live in sessionStorage, so closing the tab ends the session.
  it('keeps the tokens in the session storage of the tab (ADR-0118)', () => {
    const configuration = authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI);

    expect(configuration.cache?.cacheLocation).toBe(BrowserCacheLocation.SessionStorage);
  });

  it('signs in at the issuer of the installation as a public client with its redirect address', () => {
    const configuration = authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI);

    expect(configuration.auth).toEqual({
      clientId: 'dashboard-client',
      authority: 'https://login.fake-idp.test/tenant-1/v2.0',
      knownAuthorities: ['login.fake-idp.test'],
      redirectUri: TEST_REDIRECT_URI,
    });
  });
});

describe('returnPathOf', () => {
  it('keeps a page of the dashboard', () => {
    expect(returnPathOf('/flows/flow-alfa')).toBe('/flows/flow-alfa');
  });

  it.each([null, undefined, '', 'https://example.test/', '//example.test/flows'])(
    'falls back to the start page instead of %s',
    (value) => {
      expect(returnPathOf(value)).toBe('/');
    },
  );
});

describe('completeSignIn', () => {
  it('makes the signed-in account the active one', async () => {
    const client = await authClientFor('anna');

    expect(client.getActiveAccount()?.username).toBe('anna@example.test');
  });

  it('leaves nobody signed in when nobody signed in', async () => {
    const client = await authClientFor();

    expect(client.getActiveAccount()).toBeNull();
    expect(await completeSignIn(client)).toBeNull();
  });
});

describe('acquireAccessToken', () => {
  it('gives the access token of the signed-in account', async () => {
    const client = await authClientFor('anna');

    expect(await acquireAccessToken(client, SCOPE)).toBe(accessTokenOf('anna'));
  });

  it('tells the session expired when nobody is signed in', async () => {
    const client = await authClientFor();

    await expect(acquireAccessToken(client, SCOPE)).rejects.toBeInstanceOf(SessionExpiredError);
  });

  it('tells the session expired when the identity provider refuses to renew the token', async () => {
    const client = await authClientFor('anna');
    fakePlatform.expireSessions();

    await expect(
      acquireAccessToken(client, 'api://autotrading/another-scope'),
    ).rejects.toBeInstanceOf(SessionExpiredError);
  });
});

describe('ProtectedRoute', () => {
  const openProtectedPage = async (account?: string, page = '/flows/alfa') => {
    const client = await authClientFor(account);
    const router = createMemoryRouter(
      [
        {
          path: '/flows/:flowId',
          element: (
            <ProtectedRoute>
              <p>pagina protetta</p>
            </ProtectedRoute>
          ),
        },
        { path: '/login', element: <p>pagina di accesso</p> },
      ],
      { initialEntries: [page] },
    );
    render(
      <AuthProvider client={client} scope={SCOPE}>
        <RouterProvider router={router} />
      </AuthProvider>,
    );
    return router;
  };

  it('shows the page to a signed-in user', async () => {
    await openProtectedPage('anna');

    expect(await screen.findByText('pagina protetta')).toBeInTheDocument();
  });

  it('sends a visitor to the sign-in page, remembering the page asked for', async () => {
    const router = await openProtectedPage();

    expect(await screen.findByText('pagina di accesso')).toBeInTheDocument();
    expect(router.state.location.search).toBe('?returnTo=%2Fflows%2Falfa');
  });

  it('remembers the query string of the page too, as the filters of a page live there', async () => {
    const router = await openProtectedPage(undefined, '/flows/alfa?period=7d');

    expect(await screen.findByText('pagina di accesso')).toBeInTheDocument();
    expect(router.state.location.search).toBe('?returnTo=%2Fflows%2Falfa%3Fperiod%3D7d');
  });
});
