import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import { usePeriod } from '@/components/ui/period-selector/use-period';

import { useHistorySearch } from './use-history-search';

// Each button makes its choices in one click, before the page can show any of them.
const Probe = () => {
  const [search, changeSearch] = useHistorySearch();
  const [, choosePeriod] = usePeriod();
  const { search: query } = useLocation();
  return (
    <>
      <output aria-label="query string">{query}</output>
      <output aria-label="ricerca letta">{JSON.stringify(search)}</output>
      <button
        type="button"
        onClick={() => {
          changeSearch({ kind: 'orders' });
          changeSearch({ account: 'acc-1' });
        }}
      >
        Ordini e conto
      </button>
      <button
        type="button"
        onClick={() => {
          changeSearch({ kind: 'closed-positions' });
          choosePeriod({ kind: '7d', from: '', to: '' });
        }}
      >
        Posizioni e periodo
      </button>
    </>
  );
};

const openAt = (url: string) => {
  const router = createMemoryRouter([{ path: '/history', element: <Probe /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
};

const searchShown = () => new URLSearchParams(screen.getByLabelText('query string').textContent);

const click = (name: string) => userEvent.click(screen.getByRole('button', { name }));

describe('useHistorySearch', () => {
  it('reads the tab and the filters of the query string', () => {
    openAt('/history?tab=orders&account=acc-1');

    expect(JSON.parse(screen.getByLabelText('ricerca letta').textContent ?? '')).toEqual({
      kind: 'orders',
      flow: '',
      account: 'acc-1',
      asset: '',
      version: '',
    });
  });

  it('keeps a tab and a filter chosen before the page shows the first (ADR-0166)', async () => {
    openAt('/history');

    await click('Ordini e conto');

    expect(searchShown().get('tab')).toBe('orders');
    expect(searchShown().get('account')).toBe('acc-1');
  });

  it('keeps a tab and a period chosen before the page shows the first (ADR-0166)', async () => {
    openAt('/history');

    await click('Posizioni e periodo');

    expect(searchShown().get('tab')).toBe('closed-positions');
    expect(searchShown().get('period')).toBe('7d');
  });
});
