import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import {
  aHistoryCycle,
  aHistoryOrder,
  aHistoryPosition,
  anExecution,
  type FakeOwner,
} from '@/testing/mocks/history';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY = 24 * 3600 * 1000;
const FIRST = Date.parse('2026-11-01T11:00:00Z');
const dayOf = (number: number): Date => new Date(FIRST + (number - 1) * DAY);

const ALFA: FakeOwner = {
  flowId: 'flow-alfa',
  flow: 'alfa',
  accountId: 'account-principale',
  account: 'principale',
  version: 1,
};

const prepareAnna = (): void => {
  fakePlatform.giveFlowTo('anna', 'alfa');
  fakePlatform.changeFlow('alfa', {
    accountId: fakePlatform.addAccount('anna', 'principale').id,
    assets: ['BTC', 'ETH'],
    version: 2,
  });
};

const records = () => fakePlatform.recordsOf('anna');

const ownerAt = (day: number): FakeOwner => ({ ...ALFA, version: day < 15 ? 1 : 2 });

const rowsOf = async (table: string) => {
  const found = await screen.findByRole('table', { name: table });
  return within(found).getAllByRole('row').slice(1);
};

const tab = (name: string) => screen.getByRole('tab', { name });

describe('HistoryView', () => {
  beforeEach(prepareAnna);

  it('opens on the cycles, newest first, with flow and version, each leading to its page', async () => {
    records().cycles.push(
      ...[1, 2, 3].map((day) => aHistoryCycle(ownerAt(day), dayOf(day), ['BTC'])),
    );
    await renderApp({ account: 'anna', url: '/history' });

    const [first, , last] = await rowsOf('Cicli');
    expect(first).toHaveTextContent('03/11/2026, 12:00:00');
    expect(first).toHaveTextContent('alfa');
    expect(first).toHaveTextContent('concluso');
    expect(last).toHaveTextContent('01/11/2026, 12:00:00');
    expect(tab('Cicli')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('link', { name: '03/11/2026, 12:00:00' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles/2026-11-03T11%3A00%3A00Z',
    );
  });

  it('enables the version only with a flow, and shows only the cycles of the version chosen', async () => {
    records().cycles.push(
      ...Array.from({ length: 30 }, (_, index) =>
        aHistoryCycle(ownerAt(index + 1), dayOf(index + 1), ['BTC']),
      ),
    );
    const user = userEvent.setup();
    const { router } = await renderApp({ account: 'anna', url: '/history' });

    expect(await screen.findByLabelText('Versione')).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Flusso'), 'alfa');
    await user.selectOptions(screen.getByLabelText('Versione'), 'Versione 2');

    await waitFor(async () => expect(await rowsOf('Cicli')).toHaveLength(16));
    const rows = await rowsOf('Cicli');
    expect(rows.at(-1)).toHaveTextContent('15/11/2026');
    expect(router.state.location.search).toBe('?flow=flow-alfa&version=2');
  });

  it('shows the closed positions of an asset in a range of days, waiting for both days', async () => {
    records().closedPositions.push(
      ...Array.from({ length: 30 }, (_, index) => index + 1).flatMap((day) =>
        ['BTC', 'ETH'].map((asset) => aHistoryPosition(ownerAt(day), asset, dayOf(day))),
      ),
    );
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/history?tab=closed-positions' });

    await rowsOf('Posizioni chiuse');
    await user.selectOptions(screen.getByLabelText('Asset'), 'ETH');
    await user.selectOptions(screen.getByLabelText('Periodo'), 'Intervallo');
    expect(screen.getByText(/Scegli il giorno iniziale e il giorno finale/)).toBeInTheDocument();
    await user.type(screen.getByLabelText('Dal'), '2026-11-10');
    await user.type(screen.getByLabelText('Al'), '2026-11-20');

    await waitFor(async () => expect(await rowsOf('Posizioni chiuse')).toHaveLength(11));
    const rows = await rowsOf('Posizioni chiuse');
    rows.forEach((row) => expect(row).toHaveTextContent('ETH'));
    expect(rows[0]).toHaveTextContent('20/11/2026');
    expect(rows[0]).toHaveTextContent('+10 (10,00%)');
  });

  it('shows a loss in red', async () => {
    const position = aHistoryPosition(ALFA, 'BTC', dayOf(1));
    records().closedPositions.push({ ...position, body: { ...position.body, pnl: '-4.5' } });
    await renderApp({ account: 'anna', url: '/history?tab=closed-positions' });

    const [row] = await rowsOf('Posizioni chiuse');
    expect(within(row as HTMLElement).getByText(/-4,5/)).toHaveClass('text-red-700');
  });

  it('shows each order of an account with the price, quantity and fee of its executions', async () => {
    const executions = [
      anExecution(dayOf(1), '91000.5', '0.015', '0.41'),
      anExecution(dayOf(1), '91001', '0.005', '0.14'),
    ];
    records().orders.push(aHistoryOrder(ALFA, 'BTC', dayOf(1), executions));
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/history?tab=orders' });

    await rowsOf('Ordini');
    await user.selectOptions(screen.getByLabelText('Conto'), 'principale');
    await user.click(await screen.findByText('2 esecuzioni'));

    const table = screen.getByRole('table', { name: 'Esecuzioni' });
    const [, first, second] = within(table).getAllByRole('row');
    expect(first).toHaveTextContent('91.000,5');
    expect(first).toHaveTextContent('0.015');
    expect(first).toHaveTextContent('0,41');
    expect(second).toHaveTextContent('91.001');
    expect(screen.getByRole('row', { name: /principale/ })).toHaveTextContent('apertura long');
  });

  it('shows an order of no flow, a closing and an order without executions', async () => {
    const order = aHistoryOrder(ALFA, 'ETH', dayOf(2), []);
    const single = aHistoryOrder(ALFA, 'BTC', dayOf(1), [
      anExecution(dayOf(1), '3000', '1', '0.1'),
    ]);
    records().orders.push(
      { ...order, body: { ...order.body, flow: null, flow_id: null, closing: true } },
      single,
    );
    await renderApp({ account: 'anna', url: '/history?tab=orders' });

    const [first, second] = await rowsOf('Ordini');
    expect(first).toHaveTextContent('nessun flusso');
    expect(first).toHaveTextContent('chiusura long');
    expect(first).toHaveTextContent('Nessuna esecuzione');
    expect(second).toHaveTextContent('1 esecuzione');
  });

  it('loads 50 rows at a time, the next ones on request', async () => {
    records().cycles.push(
      ...Array.from({ length: 60 }, (_, index) =>
        aHistoryCycle(ALFA, new Date(FIRST + index * 3600_000), ['BTC']),
      ),
    );
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/history' });

    expect(await rowsOf('Cicli')).toHaveLength(50);
    await user.click(screen.getByRole('button', { name: 'Carica altri' }));

    await waitFor(async () => expect(await rowsOf('Cicli')).toHaveLength(60));
    expect(screen.queryByRole('button', { name: 'Carica altri' })).not.toBeInTheDocument();
  });

  it('says why the API refuses a search, a version without its flow', async () => {
    await renderApp({ account: 'anna', url: '/history?version=2' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Interrogazione rifiutata: la versione richiede un flusso',
    );
  });

  it('says a read failed when the history does not answer', async () => {
    server.use(
      http.get('*/history/cycles', () =>
        HttpResponse.json({ detail: 'servizio non disponibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/history' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: servizio non disponibile',
    );
  });

  it('says so when the flows of the filters do not answer', async () => {
    server.use(
      http.get('*/flows', () =>
        HttpResponse.json({ detail: 'flussi non disponibili' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/history' });

    expect(await screen.findByRole('alert')).toHaveTextContent('flussi non disponibili');
  });

  it('says so when the accounts of the filters do not answer', async () => {
    server.use(
      http.get('*/accounts', () =>
        HttpResponse.json({ detail: 'conti non disponibili' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/history' });

    expect(await screen.findByRole('alert')).toHaveTextContent('conti non disponibili');
  });

  it('shows a failed cycle with its step and an unknown version as a dash', async () => {
    const cycle = aHistoryCycle(ALFA, dayOf(1), ['BTC']);
    records().cycles.push({
      ...cycle,
      body: {
        ...cycle.body,
        version: null,
        outcome: 'fallito',
        failure: { step: "decisione dell'agente", error_type: 'X', message: 'm' },
      },
    });
    await renderApp({ account: 'anna', url: '/history' });

    const [row] = await rowsOf('Cicli');
    expect(row).toHaveTextContent("fallito nel passo «decisione dell'agente»");
    expect(row).toHaveTextContent('—');
  });

  it('switches tab keeping the filters in the query string', async () => {
    const user = userEvent.setup();
    const { router } = await renderApp({ account: 'anna', url: '/history?asset=BTC' });

    await screen.findByText('Nessun ciclo trovato.');
    await user.click(tab('Ordini'));

    expect(await screen.findByText('Nessun ordine trovato.')).toBeInTheDocument();
    expect(router.state.location.search).toBe('?asset=BTC&tab=orders');
    await user.click(tab('Posizioni chiuse'));
    expect(await screen.findByText('Nessuna posizione chiusa trovata.')).toBeInTheDocument();
  });

  it('is reached from the home page', async () => {
    await renderApp({ account: 'anna', url: '/' });

    expect(await screen.findByRole('link', { name: 'Storico' })).toHaveAttribute(
      'href',
      '/history',
    );
  });
});
