import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import {
  filterValuesOf,
  useTableFilters,
  withFilter,
  withoutFilters,
  type TableFilter,
} from './use-table-filters';

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
  { name: 'decision', label: 'Decisione', all: 'Tutte', options: [] },
];

describe('the filters of a table in the address', () => {
  it('reads the value of every declared filter present, and nothing else', () => {
    const params = new URLSearchParams('outcome=fallito&page=2&tab=x');

    expect(filterValuesOf(FILTERS, params)).toEqual({ outcome: 'fallito' });
  });

  it('chooses a value and goes back to the first page, keeping the other parameters', () => {
    const next = withFilter(new URLSearchParams('page=3&period=7d'), 'outcome', 'fallito');

    expect(next.toString()).toBe('period=7d&outcome=fallito');
  });

  it('forgets a filter chosen as all', () => {
    const next = withFilter(new URLSearchParams('outcome=fallito&page=2'), 'outcome', undefined);

    expect(next.toString()).toBe('');
  });

  it('clears every declared filter and the page, and keeps the rest', () => {
    const next = withoutFilters(
      new URLSearchParams('outcome=fallito&decision=nessuna&page=2&period=7d'),
      FILTERS,
    );

    expect(next.toString()).toBe('period=7d');
  });
});

const Probe = () => {
  const { search } = useLocation();
  const { values, choose, reset } = useTableFilters(FILTERS);
  return (
    <>
      <output aria-label="indirizzo">{search}</output>
      <output aria-label="valori">{JSON.stringify(values)}</output>
      <button type="button" onClick={() => choose('outcome', 'fallito')}>
        Falliti
      </button>
      <button type="button" onClick={reset}>
        Azzera
      </button>
    </>
  );
};

describe('useTableFilters', () => {
  it('changes the address of the page and reads it back', async () => {
    const router = createMemoryRouter([{ path: '/', element: <Probe /> }], {
      initialEntries: ['/?page=2'],
    });
    render(<RouterProvider router={router} />);

    await userEvent.click(screen.getByRole('button', { name: 'Falliti' }));

    expect(screen.getByRole('status', { name: 'indirizzo' })).toHaveTextContent('?outcome=fallito');
    expect(screen.getByRole('status', { name: 'valori' })).toHaveTextContent(
      '{"outcome":"fallito"}',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Azzera' }));
    expect(screen.getByRole('status', { name: 'indirizzo' })).toBeEmptyDOMElement();
  });
});
