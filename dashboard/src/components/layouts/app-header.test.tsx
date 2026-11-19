import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, Link, RouterProvider } from 'react-router';

import { RuntimeConfigProvider } from '@/config/runtime-config';
import { AuthProvider } from '@/lib/auth';
import { queryConfig } from '@/lib/react-query';
import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { authClientFor, TEST_CONFIG } from '@/testing/test-utils';

import { AppHeader } from './app-header';

const page = (name: string) => (
  <>
    <AppHeader />
    <h1>{name}</h1>
    <Link to="/history">Apri lo storico</Link>
  </>
);

const openDashboardAt = (initialEntries: string[]) => {
  const router = createMemoryRouter(
    [
      { path: '/', element: page('Flussi') },
      { path: '/flows/alfa', element: page('Flusso alfa') },
      { path: '/history', element: page('Storico') },
    ],
    { initialEntries, initialIndex: initialEntries.length - 1 },
  );
  render(
    <RuntimeConfigProvider config={TEST_CONFIG}>
      <RouterProvider router={router} />
    </RuntimeConfigProvider>,
  );
  return router;
};

const backCommand = () => screen.queryByRole('button', { name: 'Indietro' });

describe('AppHeader', () => {
  it('leads to the main page from the name of the platform', async () => {
    const router = openDashboardAt(['/history']);

    await userEvent.click(screen.getByRole('link', { name: 'AutoTrading' }));

    expect(router.state.location.pathname).toBe('/');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Flussi');
  });

  it('shows no command to go back on the main page', () => {
    openDashboardAt(['/']);

    expect(backCommand()).not.toBeInTheDocument();
  });

  it('goes back to the previous page of the dashboard', async () => {
    const router = openDashboardAt(['/flows/alfa']);
    await userEvent.click(screen.getByRole('link', { name: 'Apri lo storico' }));

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/flows/alfa');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Flusso alfa');
  });

  it('leads to the main page when the dashboard was opened on the page itself', async () => {
    const router = openDashboardAt(['/history']);

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Flussi');
  });

  it('keeps the command to go back large enough to be touched on a phone', () => {
    openDashboardAt(['/history']);

    expect(backCommand()).toHaveClass('min-h-11', 'min-w-11');
  });

  // ADR intestazione-su-una-riga.
  it('keeps the bar on one line, the name of the platform cut with dots when there is no room', () => {
    openDashboardAt(['/history']);

    expect(screen.getByRole('banner')).toHaveClass('flex-nowrap');
    expect(screen.getByRole('banner')).not.toHaveClass('flex-wrap');
    expect(screen.getByRole('link', { name: 'AutoTrading' })).toHaveClass('truncate', 'min-w-0');
  });

  it('keeps the command to go back whole when the name of the platform is cut', () => {
    openDashboardAt(['/history']);

    expect(backCommand()).toHaveClass('shrink-0');
  });

  it('shows the name of the platform without a link outside the pages of the dashboard', () => {
    render(
      <RuntimeConfigProvider config={TEST_CONFIG}>
        <AppHeader />
      </RuntimeConfigProvider>,
    );

    expect(screen.getByText('AutoTrading')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(backCommand()).not.toBeInTheDocument();
  });

  // ADR area-utente-in-alto-a-destra.
  it('shows the area of the signed-in user on the right of the bar, after the environment', async () => {
    const client = await authClientFor('anna');
    render(
      <AuthProvider client={client} scope={FAKE_IDENTITY_PROVIDER.scope}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: queryConfig })}>
          <RuntimeConfigProvider config={TEST_CONFIG}>
            <AppHeader />
          </RuntimeConfigProvider>
        </QueryClientProvider>
      </AuthProvider>,
    );

    const user = within(screen.getByRole('banner')).getByRole('button', { name: 'anna' });
    const environment = screen.getByLabelText("Ambiente dell'installazione");
    expect(environment.compareDocumentPosition(user) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
  });

  it('shows no area of the user before the sign-in', () => {
    render(
      <RuntimeConfigProvider config={TEST_CONFIG}>
        <AppHeader />
      </RuntimeConfigProvider>,
    );

    expect(screen.queryByRole('button', { name: 'anna' })).not.toBeInTheDocument();
  });

  // ADR campanello-delle-notifiche-nella-dashboard: the bell only on the pages of the data, between environment and user.
  it('shows the bell of the notifications between the environment and the user on the pages of the data', async () => {
    const client = await authClientFor('anna');
    const router = createMemoryRouter([{ path: '/', element: <AppHeader withNotifications /> }]);
    render(
      <AuthProvider client={client} scope={FAKE_IDENTITY_PROVIDER.scope}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: queryConfig })}>
          <RuntimeConfigProvider config={TEST_CONFIG}>
            <RouterProvider router={router} />
          </RuntimeConfigProvider>
        </QueryClientProvider>
      </AuthProvider>,
    );

    const banner = screen.getByRole('banner');
    const bell = await within(banner).findByRole('button', { name: 'Notifiche, 0 non lette' });
    const environment = screen.getByLabelText("Ambiente dell'installazione");
    const user = within(banner).getByRole('button', { name: 'anna' });
    expect(environment.compareDocumentPosition(bell) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
    expect(bell.compareDocumentPosition(user) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it('shows no bell before the dashboard admits the user', () => {
    openDashboardAt(['/']);

    expect(screen.queryByRole('button', { name: /^Notifiche/ })).not.toBeInTheDocument();
  });
});
