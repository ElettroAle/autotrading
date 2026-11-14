import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, Link, RouterProvider } from 'react-router';

import { RuntimeConfigProvider } from '@/config/runtime-config';
import { TEST_CONFIG } from '@/testing/test-utils';

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
});
