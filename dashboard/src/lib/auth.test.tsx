import {
  BrowserCacheLocation,
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AuthenticationResult,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';

import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { accessTokenOf, fakePlatform } from '@/testing/mocks/platform';
import { authClientFor, TEST_REDIRECT_URI } from '@/testing/test-utils';

import {
  acquireAccessToken,
  authConfiguration,
  AuthProvider,
  AUTOMATIC_SIGN_IN_KEY,
  completeSignIn,
  ProtectedRoute,
  returnPathOf,
  SessionExpiredError,
  startAutomaticSignIn,
  useSignedInUserName,
  useSignOut,
} from './auth';

const SCOPE = FAKE_IDENTITY_PROVIDER.scope;

const neverCalled = () => {
  throw new Error('the redirect was expected to start');
};

const stubRedirects = (client: IPublicClientApplication) =>
  vi.spyOn(client, 'acquireTokenRedirect').mockResolvedValue();

const newClient = () =>
  new PublicClientApplication(authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI));

describe('authConfiguration', () => {
  // ADR accesso-persistente-con-cache-msal-in-localstorage: the tokens outlive the tab and the browser.
  it('keeps the tokens in the local storage of the browser (ADR accesso-persistente-con-cache-msal-in-localstorage)', () => {
    const configuration = authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI);

    expect(configuration.cache?.cacheLocation).toBe(BrowserCacheLocation.LocalStorage);
  });

  it('signs in and out at the issuer of the installation as a public client with its redirect address', () => {
    const configuration = authConfiguration(FAKE_IDENTITY_PROVIDER, TEST_REDIRECT_URI);

    expect(configuration.auth).toEqual({
      clientId: 'dashboard-client',
      authority: 'https://login.fake-idp.test/tenant-1/v2.0',
      knownAuthorities: ['login.fake-idp.test'],
      redirectUri: TEST_REDIRECT_URI,
      postLogoutRedirectUri: TEST_REDIRECT_URI,
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

  it('keeps the signed-in account in the local storage, where a new tab or browser finds it', async () => {
    await authClientFor('anna');

    const reopened = await authClientFor();

    expect(reopened.getActiveAccount()?.username).toBe('anna@example.test');
  });

  it('leaves nobody signed in when nobody signed in', async () => {
    const client = await authClientFor();

    expect(client.getActiveAccount()).toBeNull();
    expect(await completeSignIn(client)).toBeNull();
  });

  it('starts no other automatic sign-in after one that brought nobody back', async () => {
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, '/flows/flow-alfa');
    const client = await authClientFor();
    const redirect = stubRedirects(client);

    expect(startAutomaticSignIn(client, SCOPE, '/flows/flow-alfa', neverCalled)).toBe(false);
    expect(redirect).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY)).toBeNull();
  });

  it('opens the page an automatic sign-in that failed was returning to', async () => {
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, '/flows/flow-alfa');
    const client = newClient();
    vi.spyOn(client, 'handleRedirectPromise').mockRejectedValue(
      new InteractionRequiredAuthError('login_required', ''),
    );

    expect(await completeSignIn(client)).toBe('/flows/flow-alfa');
  });

  it('allows a new automatic sign-in once a sign-in came back', async () => {
    const [account] = (await authClientFor('anna')).getAllAccounts();
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, '/flows/flow-alfa');
    const client = newClient();
    vi.spyOn(client, 'handleRedirectPromise').mockResolvedValue({
      account,
      state: '/flows/flow-alfa',
    } as AuthenticationResult);
    const redirect = stubRedirects(client);

    expect(await completeSignIn(client)).toBe('/flows/flow-alfa');
    expect(startAutomaticSignIn(client, SCOPE, '/', neverCalled)).toBe(true);
    expect(redirect).toHaveBeenCalledOnce();
  });

  it('lets an unexpected failure of the return through', async () => {
    const client = newClient();
    vi.spyOn(client, 'handleRedirectPromise').mockRejectedValue(new TypeError('broken'));

    await expect(completeSignIn(client)).rejects.toBeInstanceOf(TypeError);
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
    fakePlatform.expireRefreshTokens();

    await expect(
      acquireAccessToken(client, 'api://autotrading/another-scope'),
    ).rejects.toBeInstanceOf(SessionExpiredError);
  });
});

describe('startAutomaticSignIn', () => {
  it('redirects to the identity provider for the scope of the API, returning to the current page', async () => {
    const client = await authClientFor('anna');
    const redirect = stubRedirects(client);

    expect(startAutomaticSignIn(client, SCOPE, '/flows/flow-alfa?period=7d', neverCalled)).toBe(
      true,
    );
    expect(redirect).toHaveBeenCalledWith({
      scopes: [SCOPE],
      state: '/flows/flow-alfa?period=7d',
      account: client.getActiveAccount(),
    });
    expect(sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY)).toBe('/flows/flow-alfa?period=7d');
  });

  it('starts a single redirect in a load, however many readings find the session expired', async () => {
    const client = await authClientFor('anna');
    const redirect = stubRedirects(client);

    startAutomaticSignIn(client, SCOPE, '/', neverCalled);

    expect(startAutomaticSignIn(client, SCOPE, '/accounts', neverCalled)).toBe(true);
    expect(redirect).toHaveBeenCalledOnce();
  });

  it('asks without an account when nobody is signed in', async () => {
    const client = await authClientFor();
    const redirect = stubRedirects(client);

    startAutomaticSignIn(client, SCOPE, '/', neverCalled);

    expect(redirect).toHaveBeenCalledWith(expect.objectContaining({ account: undefined }));
  });

  it('gives up, forgetting the page, when the redirect cannot start', async () => {
    const client = await authClientFor('anna');
    vi.spyOn(client, 'acquireTokenRedirect').mockRejectedValue(
      new InteractionRequiredAuthError('interaction_in_progress', ''),
    );
    const onFailure = vi.fn();

    startAutomaticSignIn(client, SCOPE, '/', onFailure);

    await vi.waitFor(() => expect(onFailure).toHaveBeenCalledOnce());
    expect(sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY)).toBeNull();
    expect(startAutomaticSignIn(client, SCOPE, '/', neverCalled)).toBe(false);
  });

  it('allows a redirect on a client that never completed a sign-in', () => {
    const client = newClient();
    const redirect = stubRedirects(client);

    expect(startAutomaticSignIn(client, SCOPE, '/', neverCalled)).toBe(true);
    expect(redirect).toHaveBeenCalledOnce();
  });
});

const showWithAuth = (client: IPublicClientApplication, routes: RouteObject[], page: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [page] });
  render(
    <AuthProvider client={client} scope={SCOPE}>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
  return router;
};

describe('ProtectedRoute', () => {
  const openProtectedPage = (client: IPublicClientApplication, page = '/flows/alfa') =>
    showWithAuth(
      client,
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
      page,
    );

  it('shows the page to a signed-in user', async () => {
    openProtectedPage(await authClientFor('anna'));

    expect(await screen.findByText('pagina protetta')).toBeInTheDocument();
  });

  it('sends a visitor to the identity provider, returning to the page and its query string', async () => {
    const client = await authClientFor();
    const redirect = stubRedirects(client);

    openProtectedPage(client, '/flows/alfa?period=7d');

    await vi.waitFor(() =>
      expect(redirect).toHaveBeenCalledWith(
        expect.objectContaining({ scopes: [SCOPE], state: '/flows/alfa?period=7d' }),
      ),
    );
    expect(screen.queryByText('pagina protetta')).not.toBeInTheDocument();
  });

  it('sends a visitor to the sign-in page once an automatic sign-in brought nobody back', async () => {
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, '/flows/alfa');
    const client = await authClientFor();
    const redirect = stubRedirects(client);

    const router = openProtectedPage(client);

    expect(await screen.findByText('pagina di accesso')).toBeInTheDocument();
    expect(router.state.location.search).toBe('?returnTo=%2Fflows%2Falfa');
    expect(redirect).not.toHaveBeenCalled();
  });

  it('sends the visitor to the sign-in page when the redirect cannot start', async () => {
    const client = await authClientFor();
    vi.spyOn(client, 'acquireTokenRedirect').mockRejectedValue(
      new InteractionRequiredAuthError('interaction_in_progress', ''),
    );

    const router = openProtectedPage(client);

    expect(await screen.findByText('pagina di accesso')).toBeInTheDocument();
    expect(router.state.location.search).toBe('?returnTo=%2Fflows%2Falfa');
  });
});

describe('useSignOut', () => {
  const SignOut = () => {
    const signOut = useSignOut();
    return (
      <button type="button" onClick={() => void signOut()}>
        Esci
      </button>
    );
  };

  it('ends the session at the identity provider and keeps the sign-in page for the return', async () => {
    const client = await authClientFor('anna');
    const logout = vi.spyOn(client, 'logoutRedirect').mockResolvedValue();
    showWithAuth(client, [{ path: '/', element: <SignOut /> }], '/');

    await userEvent.click(screen.getByRole('button', { name: 'Esci' }));

    expect(logout).toHaveBeenCalledWith();
    expect(sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY)).toBe('/');
  });

  it('leaves no token in the browser', async () => {
    const client = await authClientFor('anna');
    showWithAuth(client, [{ path: '/', element: <SignOut /> }], '/');

    await userEvent.click(screen.getByRole('button', { name: 'Esci' }));

    await vi.waitFor(() => expect(client.getAllAccounts()).toEqual([]));
    expect(Object.keys(localStorage).filter((key) => key.includes('token'))).toEqual([]);
  });

  // Bug 610: MSAL empties its cache before it leaves for the identity provider; a protected page must not take the
  // empty cache for a visitor and start a sign-in that races the sign-out.
  it('starts no sign-in while the browser leaves for the identity provider', async () => {
    const client = await authClientFor('anna');
    client.setNavigationClient({
      navigateInternal: () => Promise.resolve(true),
      navigateExternal: () => new Promise<boolean>(() => undefined),
    });
    const redirect = stubRedirects(client);
    showWithAuth(
      client,
      [
        {
          path: '/',
          element: (
            <ProtectedRoute>
              <SignOut />
            </ProtectedRoute>
          ),
        },
        { path: '/login', element: <p>pagina di accesso</p> },
      ],
      '/',
    );

    await userEvent.click(await screen.findByRole('button', { name: 'Esci' }));

    await vi.waitFor(() => expect(client.getAllAccounts()).toEqual([]));
    await vi.waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Esci' })).not.toBeInTheDocument(),
    );
    expect(redirect).not.toHaveBeenCalled();
    expect(screen.queryByText('pagina di accesso')).not.toBeInTheDocument();
    expect(sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY)).toBe('/');
  });
});

// ADR area-utente-in-alto-a-destra: the name comes from the identity token MSAL already holds, never from the API.
describe('useSignedInUserName', () => {
  const UserName = () => <p>{useSignedInUserName() ?? 'nessuno'}</p>;

  it('is the name of the signed-in user', async () => {
    const client = await authClientFor('anna');
    showWithAuth(client, [{ path: '/', element: <UserName /> }], '/');

    expect(await screen.findByText('anna')).toBeInTheDocument();
  });

  it('falls back on the username when the token has no name', async () => {
    const client = await authClientFor('anna');
    const account = client.getActiveAccount();
    if (account === null) {
      throw new Error('anna was expected to be signed in');
    }
    vi.spyOn(client, 'getActiveAccount').mockReturnValue({ ...account, name: undefined });
    showWithAuth(client, [{ path: '/', element: <UserName /> }], '/');

    expect(await screen.findByText('anna@example.test')).toBeInTheDocument();
  });

  it('is nobody before the sign-in', async () => {
    const client = await authClientFor();
    showWithAuth(client, [{ path: '/', element: <UserName /> }], '/');

    expect(await screen.findByText('nessuno')).toBeInTheDocument();
  });
});
