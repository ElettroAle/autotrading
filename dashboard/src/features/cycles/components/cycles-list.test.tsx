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

  it('shows the action and the direction of each decision with their icons (R6.5.3)', async () => {
    fakePlatform.recordCycles('alfa', cyclesBack(1));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const [first] = await rowsOf();
    expect(
      within(within(first as HTMLElement).getByText('apri')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'plus');
    expect(
      within(within(first as HTMLElement).getByText('long')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'arrow-up');
  });

  // R6.5.2, ADR pulsante-esegui-ora-nella-pagina-del-flusso.
  it('marks a cycle the user asked for now, and only that one', async () => {
    const asked = { ...aCompletedCycle(LAST), trigger: 'on_demand' as const };
    fakePlatform.recordCycles('alfa', [asked, aCompletedCycle(new Date(LAST.getTime() - QUARTER))]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const [first, second] = await rowsOf();
    expect(first).toHaveTextContent('14/11/2026, 10:07:00 · su richiesta');
    expect(second).not.toHaveTextContent('su richiesta');
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
    await user.click(within(row as HTMLElement).getByText('BTC'));

    expect(router.state.location.pathname).toBe('/flows/flow-alfa/cycles/2026-11-14T09%3A07%3A00Z');
  });

  // ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune: the period of the page holds for the tab Cicli too.
  // The API reads the instants in UTC; the page shows them in the time zone of the browser, an hour ahead.
  const DAY_13_IN_ROME = /13\/11\/2026|14\/11\/2026, 00:/;

  describe('in the period of the page, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune', () => {
    it('lists only the cycles of the days of the period', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(200));
      await renderApp({
        account: 'anna',
        url: '/flows/flow-alfa/cycles?period=range&from=2026-11-13T00:00Z&to=2026-11-13T23:59Z',
      });

      const rows = await rowsOf();
      expect(rows.length).toBeGreaterThan(0);
      rows.forEach((row) => expect(row).toHaveTextContent(DAY_13_IN_ROME));
    });

    it('lists the cycles of an interval chosen on the chart', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(200));
      await renderApp({
        account: 'anna',
        url: '/flows/flow-alfa/cycles?period=7d&from=2026-11-13T00:00Z&to=2026-11-13T23:59Z',
      });

      const rows = await rowsOf();
      rows.forEach((row) => expect(row).toHaveTextContent(DAY_13_IN_ROME));
    });

    // ADR periodo-al-minuto: the interval holds the cycles from its first minute to its last, both included.
    it('lists only the cycles of the minutes of the interval', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(200));
      await renderApp({
        account: 'anna',
        url: '/flows/flow-alfa/cycles?period=7d&from=2026-11-14T08%3A22Z&to=2026-11-14T08%3A52Z',
      });

      await expect.poll(async () => (await rowsOf()).length).toBe(3);
      const rows = await rowsOf();
      ['09:52:00', '09:37:00', '09:22:00'].forEach((time, index) =>
        expect(rows[index]).toHaveTextContent(`14/11/2026, ${time}`),
      );
    });

    it('says no cycle falls in the period', async () => {
      fakePlatform.recordCycles('alfa', cyclesBack(1));
      await renderApp({
        account: 'anna',
        url: '/flows/flow-alfa/cycles?period=range&from=2026-10-01T00:00Z&to=2026-10-02T23:59Z',
      });

      expect(await screen.findByText('Nessun ciclo nel periodo scelto.')).toBeInTheDocument();
    });

    it('waits for both days of a range', async () => {
      await renderApp({
        account: 'anna',
        url: '/flows/flow-alfa/cycles?period=range&from=2026-10-01T00:00Z',
      });

      expect(
        await screen.findByText("Scegli l'inizio e la fine dell'intervallo."),
      ).toBeInTheDocument();
      expect(screen.queryByRole('table', { name: 'Cicli' })).not.toBeInTheDocument();
    });
  });
});
