import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation, type To } from 'react-router';

import { useSearchChange, type SearchChange } from './use-search-change';

const setting =
  (name: string, value: string): SearchChange =>
  (current) => {
    const next = new URLSearchParams(current);
    next.set(name, value);
    return next;
  };

type Router = ReturnType<typeof createMemoryRouter>;

// Each button makes its changes in one click, before the page can show any of them.
const Probe = ({ router }: { router: () => Router }) => {
  const { pathname, search } = useLocation();
  const change = useSearchChange();
  const changeThenGo = (to: To) => {
    change(setting('tab', 'orders'));
    void router().navigate(to);
  };
  return (
    <>
      <output aria-label="indirizzo">{`${pathname}${search}`}</output>
      <button type="button" onClick={() => change(setting('account', 'acc-1'))}>
        Conto
      </button>
      <button type="button" onClick={() => change(setting('asset', 'BTC'))}>
        Asset
      </button>
      <button
        type="button"
        onClick={() => {
          change(setting('tab', 'orders'));
          change(setting('account', 'acc-1'));
        }}
      >
        Scheda e conto
      </button>
      <button type="button" onClick={() => changeThenGo('/history?flow=alfa')}>
        Scheda e flusso
      </button>
      <button type="button" onClick={() => changeThenGo('/ranking')}>
        Scheda e classifica
      </button>
    </>
  );
};

const openAt = (url: string): Router => {
  const router: Router = createMemoryRouter(
    [{ path: '*', element: <Probe router={() => router} /> }],
    { initialEntries: [url] },
  );
  render(<RouterProvider router={router} />);
  return router;
};

const addressShown = () => screen.getByLabelText('indirizzo').textContent;

const click = (name: string) => userEvent.click(screen.getByRole('button', { name }));

describe('useSearchChange', () => {
  it('changes the query string of the page, keeping its path and its other parameters', async () => {
    openAt('/history?tab=orders');

    await click('Conto');

    expect(addressShown()).toBe('/history?tab=orders&account=acc-1');
  });

  it('adds up two changes made before the page shows the first (ADR-0166)', async () => {
    openAt('/history');

    await click('Scheda e conto');

    expect(addressShown()).toBe('/history?tab=orders&account=acc-1');
  });

  it('starts from the address shown after the page went back', async () => {
    const router = openAt('/history?tab=orders');
    await click('Conto');

    await act(() => router.navigate(-1));
    await click('Asset');

    expect(addressShown()).toBe('/history?tab=orders&asset=BTC');
  });

  it('forgets a change not yet shown when the page moves to another address of its own', async () => {
    openAt('/history');

    await click('Scheda e flusso');
    await click('Asset');

    expect(addressShown()).toBe('/history?flow=alfa&asset=BTC');
  });

  it('forgets a change not yet shown when the page moves to another path', async () => {
    openAt('/history');

    await click('Scheda e classifica');
    await click('Conto');

    expect(addressShown()).toBe('/ranking?account=acc-1');
  });
});
