import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { BackButton } from './back-button';

const openDashboardWith = (initialEntries: string[]) => {
  const router = createMemoryRouter([{ path: '*', element: <BackButton /> }], {
    initialEntries,
    initialIndex: initialEntries.length - 1,
  });
  render(<RouterProvider router={router} />);
  return router;
};

describe('BackButton', () => {
  it('goes back one page in the history of the dashboard', async () => {
    const router = openDashboardWith(['/']);
    // The router renders a navigation in a transition: inside act the button reads the page it leads to, not the one
    // before (Bug 610).
    await act(() => router.navigate('/flows/alfa'));
    await act(() => router.navigate('/flows/alfa/versions'));

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/flows/alfa');
  });

  // ADR intestazione-su-una-riga.
  it('shows only the arrow under 768 pixels, keeping «Indietro» for screen readers', () => {
    openDashboardWith(['/flows/alfa']);

    expect(screen.getByText('Indietro')).toHaveClass('max-md:sr-only');
    expect(screen.getByRole('button', { name: 'Indietro' })).toHaveClass('min-h-11', 'min-w-11');
  });

  it('leads to the main page from the page the dashboard was opened on', async () => {
    const router = openDashboardWith(['/flows/alfa']);

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/');
  });
});
