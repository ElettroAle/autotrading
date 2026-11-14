import { PublicClientApplication, type AuthenticationResult } from '@azure/msal-browser';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { authClientFor, renderApp, TEST_CONFIG } from '@/testing/test-utils';

import { startApp } from '.';

const CONFIG_URL = `http://localhost:3000${import.meta.env.BASE_URL}config.json`;

const serveConfig = (config: object) =>
  server.use(http.get(CONFIG_URL, () => HttpResponse.json(config)));

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

  it('sends a visitor to the sign-in page', async () => {
    serveConfig(TEST_CONFIG);

    render(await startApp());

    expect(
      await screen.findByRole('heading', { name: 'Accesso alla dashboard' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/dashboard/login');
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

    expect(await screen.findByRole('heading', { level: 2 })).toHaveTextContent('alfa');
    expect(window.location.pathname).toBe('/dashboard/flows/flow-alfa');
  });
});

describe('App', () => {
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
