import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { ViewTabs } from './view-tabs';

const VIEWS = [
  { name: 'Elenco', to: '/' },
  { name: 'Classifica', to: '/ranking' },
] as const;

const openAt = (url: string) => {
  const router = createMemoryRouter(
    [{ path: '*', element: <ViewTabs label="Viste dei flussi" views={VIEWS} /> }],
    { initialEntries: [url] },
  );
  render(<RouterProvider router={router} />);
  return router;
};

describe('ViewTabs', () => {
  it('shows every view as a link to its own address', () => {
    openAt('/');

    const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
    expect(views).toContainElement(screen.getByRole('link', { name: 'Elenco' }));
    expect(screen.getByRole('link', { name: 'Elenco' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute('href', '/ranking');
  });

  it('marks the view of the current page, and only that one', () => {
    openAt('/ranking');

    expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'Elenco' })).not.toHaveAttribute('aria-current');
  });

  it('moves to another view and marks it', async () => {
    const router = openAt('/');

    await userEvent.click(screen.getByRole('link', { name: 'Classifica' }));

    expect(router.state.location.pathname).toBe('/ranking');
    expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('wraps the views on a narrow screen instead of pushing the page wider', () => {
    openAt('/');

    const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
    expect(within(views).getByRole('list')).toHaveClass('flex-wrap');
  });
});
