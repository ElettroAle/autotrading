import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { Pagination } from './pagination';

const renderAt = (page: number, hasNext: boolean) => {
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <Pagination page={page} hasNext={hasNext} hrefOf={(target) => `/items?page=${target}`} />
      ),
    },
  ]);
  render(<RouterProvider router={router} />);
};

describe('Pagination', () => {
  it('leads to the next page while there is one', () => {
    renderAt(1, true);

    expect(screen.getByRole('link', { name: 'Pagina successiva' })).toHaveAttribute(
      'href',
      '/items?page=2',
    );
    expect(screen.queryByRole('link', { name: 'Pagina precedente' })).not.toBeInTheDocument();
    expect(screen.getByText('Pagina 1')).toBeInTheDocument();
  });

  it('leads back to the previous page and offers no next one on the last page', () => {
    renderAt(3, false);

    expect(screen.getByRole('link', { name: 'Pagina precedente' })).toHaveAttribute(
      'href',
      '/items?page=2',
    );
    expect(screen.queryByRole('link', { name: 'Pagina successiva' })).not.toBeInTheDocument();
  });
});
