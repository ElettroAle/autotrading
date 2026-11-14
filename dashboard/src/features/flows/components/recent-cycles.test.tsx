import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

describe('RecentCycles', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
  });

  it('lists the cycles of the flow from the most recent, with instant and outcome', async () => {
    const earlier = new Date(2026, 10, 14, 9, 45, 0);
    const later = new Date(2026, 10, 14, 10, 0, 10);
    fakePlatform.concludeCycle('alfa', earlier);
    fakePlatform.concludeCycle('alfa', later);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const cycles = within(await screen.findByRole('list', { name: 'Cicli recenti' })).getAllByRole(
      'listitem',
    );

    expect(cycles.map((cycle) => cycle.textContent)).toEqual([
      `${formatInstant(later.toISOString())}concluso`,
      `${formatInstant(earlier.toISOString())}concluso`,
    ]);
  });

  it('says the flow has no cycle yet', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Nessun ciclo ancora eseguito.')).toBeInTheDocument();
  });

  it('tells why the cycles could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/cycles', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });
});
