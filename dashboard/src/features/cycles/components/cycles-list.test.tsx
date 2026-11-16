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

  // R6.4.2: the failed cycles of the summary lead here, filtered on the failed.
  it('lists only the failed cycles when the page asks for them, keeping the filter across the pages', async () => {
    const failed = (index: number) =>
      aFailedCycle(
        aCompletedCycle(new Date(LAST.getTime() - index * QUARTER)),
        STEPS.agentDecision,
        {
          errorType: 'X',
          message: 'y',
        },
      );
    fakePlatform.recordCycles('alfa', [
      ...cyclesBack(3),
      ...Array.from({ length: 51 }, (_, index) => failed(index + 3)),
    ]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?outcome=fallito' });

    const rows = await rowsOf();
    expect(rows).toHaveLength(50);
    rows.forEach((row) => expect(row).toHaveTextContent('fallito'));
    expect(screen.getByText('Solo i cicli falliti.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Pagina successiva' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles?outcome=fallito&page=2',
    );
    expect(screen.getByRole('link', { name: 'Mostra tutti i cicli' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles',
    );
  });

  it('names any other outcome the page filters on', async () => {
    fakePlatform.recordCycles('alfa', [{ ...aCompletedCycle(LAST), outcome: 'saltato' }]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?outcome=saltato' });

    expect(await rowsOf()).toHaveLength(1);
    expect(screen.getByText('Solo i cicli con esito «saltato».')).toBeInTheDocument();
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

  describe('with filters', () => {
    const failedAt = (minutes: number) =>
      aFailedCycle(
        aCompletedCycle(new Date(LAST.getTime() - minutes * 60_000)),
        STEPS.agentDecision,
        { errorType: 'X', message: 'y' },
      );

    it('shows only the failed cycles, with how many they are, and back to all', async () => {
      fakePlatform.recordCycles('alfa', [...cyclesBack(3), failedAt(1), failedAt(2)]);
      const user = userEvent.setup();
      await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });
      expect(await screen.findByText('5 cicli')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Falliti' }));

      expect(await screen.findByText('2 cicli')).toBeInTheDocument();
      const rows = await rowsOf();
      expect(rows).toHaveLength(2);
      rows.forEach((row) => expect(row).toHaveTextContent('fallito'));
      await user.click(screen.getByRole('button', { name: 'Azzera i filtri' }));
      expect(await screen.findByText('5 cicli')).toBeInTheDocument();
    });

    it('reads the filters of the address, as after a reload', async () => {
      fakePlatform.recordCycles('alfa', [...cyclesBack(2), failedAt(1)]);
      await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?decision=nessuna' });

      expect(await screen.findByText('1 ciclo')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Nessuna decisione' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });

    it('shows the cycles with an opening', async () => {
      fakePlatform.recordCycles('alfa', [...cyclesBack(3), failedAt(1)]);
      const user = userEvent.setup();
      await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });
      await screen.findByText('4 cicli');

      await user.click(screen.getByRole('button', { name: 'Aperture' }));

      expect(await screen.findByText('3 cicli')).toBeInTheDocument();
      (await rowsOf()).forEach((row) => expect(row).toHaveTextContent('apri long BTC'));
    });

    it('keeps the filters on the next page', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(60));
      await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?outcome=concluso' });

      expect(await screen.findByRole('link', { name: 'Pagina successiva' })).toHaveAttribute(
        'href',
        '/flows/flow-alfa/cycles?outcome=concluso&page=2',
      );
    });

    it('says no cycle matches the filters, and keeps them', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(2));
      await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles?outcome=fallito' });

      expect(await screen.findByText('Nessun ciclo con questi filtri.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Azzera i filtri' })).toBeInTheDocument();
    });
  });

  it('opens a cycle from any point of its row', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(1));
    const user = userEvent.setup();
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const [row] = await rowsOf();
    await user.click(within(row as HTMLElement).getByText('apri long BTC'));

    expect(router.state.location.pathname).toBe('/flows/flow-alfa/cycles/2026-11-14T09%3A07%3A00Z');
  });
});
