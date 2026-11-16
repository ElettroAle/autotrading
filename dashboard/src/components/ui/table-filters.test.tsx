import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import type { TableFilter } from '@/hooks/use-table-filters';

import { TableFilters } from './table-filters';

const FILTERS: TableFilter[] = [
  {
    name: 'outcome',
    label: 'Esito',
    all: 'Tutti',
    options: [
      { value: 'concluso', label: 'Conclusi' },
      { value: 'fallito', label: 'Falliti' },
    ],
  },
];

const countOf = (total: number) => (total === 1 ? '1 ciclo' : `${total} cicli`);

const Address = () => <output aria-label="indirizzo">{useLocation().search}</output>;

const renderAt = (url: string, total = 40) => {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: (
          <>
            <TableFilters label="Cicli" filters={FILTERS} total={total} countOf={countOf} />
            <Address />
          </>
        ),
      },
    ],
    { initialEntries: [url] },
  );
  render(<RouterProvider router={router} />);
};

const choice = (name: string) => screen.getByRole('button', { name });

describe('TableFilters', () => {
  it('shows each filter as quick choices, the one in the address pressed', () => {
    renderAt('/?outcome=fallito');

    const group = screen.getByRole('group', { name: 'Esito' });
    expect(
      within(group)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Tutti', 'Conclusi', 'Falliti']);
    expect(choice('Falliti')).toHaveAttribute('aria-pressed', 'true');
    expect(choice('Tutti')).toHaveAttribute('aria-pressed', 'false');
  });

  it('presses all when the address chooses nothing', () => {
    renderAt('/');

    expect(choice('Tutti')).toHaveAttribute('aria-pressed', 'true');
  });

  it('says how many results the filters give', () => {
    renderAt('/?outcome=fallito', 2);

    expect(screen.getByText('2 cicli')).toBeInTheDocument();
  });

  it('puts the choice in the address and back to all', async () => {
    renderAt('/?page=2');

    await userEvent.click(choice('Falliti'));
    expect(screen.getByRole('status', { name: 'indirizzo' })).toHaveTextContent('?outcome=fallito');

    await userEvent.click(choice('Tutti'));
    expect(screen.getByRole('status', { name: 'indirizzo' })).toBeEmptyDOMElement();
  });

  it('offers to clear the filters only when one is chosen', async () => {
    renderAt('/');
    expect(screen.queryByRole('button', { name: 'Azzera i filtri' })).not.toBeInTheDocument();

    await userEvent.click(choice('Conclusi'));
    await userEvent.click(screen.getByRole('button', { name: 'Azzera i filtri' }));

    expect(screen.getByRole('status', { name: 'indirizzo' })).toBeEmptyDOMElement();
  });

  it('groups the filters of the table under its name', () => {
    renderAt('/');

    expect(screen.getByRole('group', { name: 'Filtri di Cicli' })).toBeInTheDocument();
  });
});
