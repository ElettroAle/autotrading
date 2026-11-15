import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import { useComparedFlows } from './use-compared-flows';
import { useRankingSort } from './use-ranking-sort';

// Each button makes its choices in one click, before the page can show any of them.
const Probe = () => {
  const [sort, sortBy] = useRankingSort();
  const [flowIds, toggle] = useComparedFlows();
  const { search } = useLocation();
  return (
    <>
      <output aria-label="query string">{search}</output>
      <output aria-label="ordine letto">{JSON.stringify(sort)}</output>
      <output aria-label="flussi letti">{JSON.stringify(flowIds)}</output>
      <button
        type="button"
        onClick={() => {
          toggle('alfa');
          toggle('beta');
        }}
      >
        Due flussi
      </button>
      <button
        type="button"
        onClick={() => {
          sortBy('pnl');
          sortBy('pnl');
        }}
      >
        Due volte PnL
      </button>
      <button
        type="button"
        onClick={() => {
          sortBy('pnl');
          toggle('alfa');
        }}
      >
        PnL e flusso
      </button>
    </>
  );
};

const openAt = (url: string) => {
  const router = createMemoryRouter([{ path: '/ranking', element: <Probe /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
};

const searchShown = () => new URLSearchParams(screen.getByLabelText('query string').textContent);

const click = (name: string) => userEvent.click(screen.getByRole('button', { name }));

describe('the query string of the ranking', () => {
  it('reads the sort and the compared flows of the query string', () => {
    openAt('/ranking?sort=pnl&order=asc&flow=alfa');

    expect(JSON.parse(screen.getByLabelText('ordine letto').textContent ?? '')).toEqual({
      key: 'pnl',
      direction: 'ascending',
    });
    expect(JSON.parse(screen.getByLabelText('flussi letti').textContent ?? '')).toEqual(['alfa']);
  });

  it('keeps two flows compared before the page shows the first (ADR-0166)', async () => {
    openAt('/ranking');

    await click('Due flussi');

    expect(searchShown().getAll('flow')).toEqual(['alfa', 'beta']);
  });

  it('turns the order of a column sorted twice before the page shows the first (ADR-0166)', async () => {
    openAt('/ranking');

    await click('Due volte PnL');

    expect(searchShown().get('sort')).toBe('pnl');
    expect(searchShown().get('order')).toBe('asc');
  });

  it('keeps a sort and a compared flow chosen before the page shows the first (ADR-0166)', async () => {
    openAt('/ranking');

    await click('PnL e flusso');

    expect(searchShown().get('sort')).toBe('pnl');
    expect(searchShown().getAll('flow')).toEqual(['alfa']);
  });
});
