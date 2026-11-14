import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const LAST = new Date('2026-11-14T09:07:00Z');
const QUARTER = 15 * 60_000;

const cyclesBack = (count: number) =>
  Array.from({ length: count }, (_, index) =>
    aCompletedCycle(new Date(LAST.getTime() - index * QUARTER)),
  );

const rowsOf = async () => {
  const table = await screen.findByRole('table', { name: 'Cicli' });
  return within(table).getAllByRole('row').slice(1);
};

describe('CyclesList', () => {
  beforeEach(() => {
    fakePlatform.giveFlowTo('anna', 'alfa');
  });

  it('lists the cycles from the most recent, with instant, outcome and decisions', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(3).reverse());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const [first] = await rowsOf();
    expect(first).toHaveTextContent('14/11/2026, 10:07:00');
    expect(first).toHaveTextContent('concluso');
    expect(first).toHaveTextContent('apri long BTC');
  });

  it('leads from each cycle to its own page', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(1));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    expect(await screen.findByRole('link', { name: '14/11/2026, 10:07:00' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles/2026-11-14T09%3A07%3A00Z',
    );
  });

  it('shows 50 cycles a page, with the next page and back', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(60));
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    expect(await rowsOf()).toHaveLength(50);
    await user.click(screen.getByRole('link', { name: 'Pagina successiva' }));

    await screen.findByText('Pagina 2');
    expect(await rowsOf()).toHaveLength(10);
    expect(screen.getByRole('link', { name: 'Pagina precedente' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles',
    );
  });

  it('reads an invalid page as the first', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(1));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?page=zero' });

    expect(await screen.findByText('Pagina 1')).toBeInTheDocument();
  });

  it('says where a failed cycle stopped, with no decision', async () => {
    const cycle = aCompletedCycle(LAST);
    fakePlatform.recordCycles('alfa', [
      aFailedCycle(cycle, STEPS.composeContext, { errorType: 'X', message: 'y' }),
    ]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const [first] = await rowsOf();
    expect(first).toHaveTextContent('fallito nel passo «composizione del contesto»');
    expect(first).toHaveTextContent('—');
  });

  it('says the flow has no cycle yet', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    expect(await screen.findByText('Nessun ciclo registrato.')).toBeInTheDocument();
  });

  it('tells why the cycles could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/cycles', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    expect(await screen.findByRole('alert')).toHaveTextContent('flusso non trovato');
  });
});
