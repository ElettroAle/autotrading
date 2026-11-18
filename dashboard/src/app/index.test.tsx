import {
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AuthenticationResult,
} from '@azure/msal-browser';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { AUTOMATIC_SIGN_IN_KEY } from '@/lib/auth';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import {
  authClientFor,
  renderApp,
  TEST_CONFIG,
  untilEveryRequestIsAnswered,
} from '@/testing/test-utils';

import { startApp } from '.';

const CONFIG_URL = `http://localhost:3000${import.meta.env.BASE_URL}config.json`;

const serveConfig = (config: object) =>
  server.use(http.get(CONFIG_URL, () => HttpResponse.json(config)));

// The spies replace methods of every client of MSAL: no test leaves them to the next. The router of startApp is bound
// to the history of the window: an answer to a reading of a page left behind could still move it, in the next test
// (Bug 610), so a test ends once every reading is answered.
afterEach(async () => {
  await untilEveryRequestIsAnswered();
  vi.restoreAllMocks();
});

describe('startApp', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/dashboard/');
  });

  it('tells the configuration is missing when the container does not serve it', async () => {
    server.use(http.get(CONFIG_URL, () => new HttpResponse(null, { status: 503 })));

    render(await startApp());

    expect(screen.getByRole('alert')).toHaveTextContent(
      'La configurazione della dashboard non è disponibile: riprova più tardi.',
    );
  });

  it('keeps the access closed while the installation has no identity provider', async () => {
    serveConfig({ ...TEST_CONFIG, issuer: '' });

    render(await startApp());

    expect(screen.getByRole('alert')).toHaveTextContent(
      "L'accesso a questa installazione non è ancora configurato.",
    );
    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('dev');
  });

  it('sends a visitor to the identity provider, returning to the page asked for', async () => {
    serveConfig(TEST_CONFIG);
    window.history.replaceState(null, '', '/dashboard/flows/flow-alfa');
    const redirect = vi
      .spyOn(PublicClientApplication.prototype, 'acquireTokenRedirect')
      .mockResolvedValue();

    render(await startApp());

    await vi.waitFor(() =>
      expect(redirect).toHaveBeenCalledWith(
        expect.objectContaining({ scopes: [TEST_CONFIG.scope], state: '/flows/flow-alfa' }),
      ),
    );
  });

  it('sends a visitor to the sign-in page, at the page asked for, when the automatic sign-in brought nobody back', async () => {
    serveConfig(TEST_CONFIG);
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, '/flows/flow-alfa');
    const redirect = vi.spyOn(PublicClientApplication.prototype, 'acquireTokenRedirect');

    render(await startApp());

    expect(
      await screen.findByRole('heading', { name: 'Accesso alla dashboard' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/dashboard/login');
    expect(new URLSearchParams(window.location.search).get('returnTo')).toBe('/flows/flow-alfa');
    expect(redirect).not.toHaveBeenCalled();
  });

  it('opens the page the user asked for once back from the identity provider', async () => {
    serveConfig(TEST_CONFIG);
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
    const [account] = (await authClientFor('anna')).getAllAccounts();
    vi.spyOn(PublicClientApplication.prototype, 'handleRedirectPromise').mockResolvedValue({
      account,
      state: '/flows/flow-alfa',
    } as AuthenticationResult);

    render(await startApp());

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/dashboard/flows/flow-alfa');
  });
});

describe('App', () => {
  it('renews the session with a redirect to the identity provider, back to the page, when no token can be had', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    vi.spyOn(PublicClientApplication.prototype, 'acquireTokenSilent').mockRejectedValue(
      new InteractionRequiredAuthError('invalid_grant', ''),
    );
    const redirect = vi
      .spyOn(PublicClientApplication.prototype, 'acquireTokenRedirect')
      .mockResolvedValue();

    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=7d' });

    await vi.waitFor(() =>
      expect(redirect).toHaveBeenCalledWith(
        expect.objectContaining({ state: '/flows/flow-alfa?period=7d' }),
      ),
    );
    expect(redirect).toHaveBeenCalledOnce();
  });

  it('sends the user back to sign in when the API no longer accepts the session, remembering the page', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    server.use(http.get('*/me', () => HttpResponse.json({}, { status: 401 })));

    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(
      await screen.findByRole('heading', { name: 'Accesso alla dashboard' }),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe('?returnTo=%2Fflows%2Fflow-alfa');
  });
});
