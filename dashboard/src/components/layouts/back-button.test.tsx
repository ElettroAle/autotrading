import { render, screen } from '@testing-library/react';
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
    await router.navigate('/flows/alfa');
    await router.navigate('/flows/alfa/versions');

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/flows/alfa');
  });

  it('leads to the main page from the page the dashboard was opened on', async () => {
    const router = openDashboardWith(['/flows/alfa']);

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/');
  });
});
