import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY = 24 * 60 * 60_000;

// ADR-spaziatura-tra-stato-e-avviso-della-rete (Bug 581): the badge of the status and the notice of the network
// share a flex container with the standard gap, with no margin of their own.
const STATUS_AND_NETWORK = ['flex', 'flex-wrap', 'items-center', 'gap-2'];

describe('FlowView', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
  });

  it('titles the page with the name of the flow and shows its status', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.getByText('Stato: attivo')).toBeInTheDocument();
  });

  // ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune: what does not depend on the period is out of the tabs.
  it('leads to the configuration of the flow with a command out of the tabs', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=7d' });

    const configuration = await screen.findByRole('link', { name: 'Configurazione' });
    expect(configuration).toHaveAttribute('href', '/flows/flow-alfa/versions');
    expect(configuration).toHaveClass('min-h-11');
    expect(screen.getByRole('navigation', { name: 'Dati del flusso' })).not.toContainElement(
      configuration,
    );
  });

  it('warns that a flow on the test network trades no real money', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('note')).toHaveTextContent(
      'Il flusso opererà sulla rete di test "sandbox", senza denaro reale',
    );
  });

  it('shows no warning of the test network for a flow on real money', async () => {
    fakePlatform.configureExchangeNetwork('real');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.queryByText(/rete di test/)).not.toBeInTheDocument();
  });

  it('leads to the tabs of the flow, carrying the period of the page', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=7d&outcome=fallito' });

    const views = await screen.findByRole('navigation', { name: 'Dati del flusso' });
    expect(
      within(views)
        .getAllByRole('link')
        .map((link) => [link.textContent, link.getAttribute('href')]),
    ).toEqual([
      ['Panoramica', '/flows/flow-alfa?period=7d'],
      ['Posizioni chiuse', '/flows/flow-alfa/closed-positions?period=7d'],
      ['Cicli', '/flows/flow-alfa/cycles?period=7d'],
      ['Decisioni', '/flows/flow-alfa/decisions?period=7d'],
      ['Capitale', '/flows/flow-alfa/capital?period=7d'],
    ]);
  });

  it('shows the positions open now in the overview, saying they hold whatever the period', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=7d' });

    const positions = await screen.findByRole('region', { name: 'Posizioni aperte attuali' });
    expect(positions).toHaveTextContent(
      'Le posizioni aperte adesso, qualunque sia il periodo scelto.',
    );
  });

  it('leads from the old address of the open positions to the overview, with its period', async () => {
    const { router } = await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/positions?period=7d',
    });

    expect(await screen.findByRole('region', { name: 'Posizioni aperte attuali' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/flows/flow-alfa');
    expect(router.state.location.search).toBe('?period=7d');
  });

  it('shows no list of the recent cycles, R6.4.3', async () => {
    fakePlatform.concludeCycle('alfa', new Date(2026, 10, 14, 9, 45, 0));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { name: 'Equity curve' })).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Cicli recenti' })).not.toBeInTheDocument();
  });

  it('says a flow outside the tenant of the user does not exist, under the generic title', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega' });

    expect(await screen.findByText('Flusso non trovato.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Flusso$/);
  });

  it('keeps the period and the tabs above the tab chosen', async () => {
    fakePlatform.concludeCycle('alfa', new Date());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });

    const period = await screen.findByLabelText('Periodo');
    const views = screen.getByRole('navigation', { name: 'Dati del flusso' });
    const cycles = await screen.findByRole('table', { name: 'Cicli' });
    expect(period.compareDocumentPosition(views)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(views.compareDocumentPosition(cycles)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(within(views).getByRole('link', { name: 'Cicli' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('shows name, status with its commands and the warning of the network, then period, tabs and tab', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const name = await screen.findByRole('heading', { level: 1, name: 'alfa' });
    const status = await screen.findByText('Stato: attivo');
    const notice = screen.getByRole('note');
    const commands = await screen.findByRole('group', { name: 'Comandi del flusso' });
    const period = screen.getByLabelText('Periodo');
    const views = screen.getByRole('navigation', { name: 'Dati del flusso' });
    const curve = screen.getByRole('heading', { name: 'Equity curve' });
    const order = [name, status, notice, commands, period, views, curve];
    order.slice(1).forEach((element, index) => {
      expect(order[index]?.compareDocumentPosition(element)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });
  });

  // R6.4.2 and R6.4.3: the summary opens the overview, below the period it is read in.
  it('shows the summary of the results at the top of the overview, in the period of the page', async () => {
    fakePlatform.changeFlow('alfa', { allocatedCapital: 100, currentCapital: 102.5 });
    const now = Date.now();
    fakePlatform.recordEquity('alfa', new Date(now - 10 * DAY), 100);
    fakePlatform.recordEquity('alfa', new Date(now - 5 * DAY), 102.1);
    fakePlatform.recordEquity('alfa', new Date(now - DAY), 102.5);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=7d' });

    const results = await screen.findByRole('region', { name: 'Riepilogo dei risultati' });
    expect(await within(results).findByLabelText('Guadagno totale')).toHaveTextContent(
      '+2,50 USDC · +2,50%',
    );
    expect(within(results).getByLabelText('Guadagno nel periodo')).toHaveTextContent(
      '+0,40 USDC · +0,40%',
    );
    const views = screen.getByRole('navigation', { name: 'Dati del flusso' });
    const curve = screen.getByRole('heading', { name: 'Equity curve' });
    expect(views.compareDocumentPosition(results)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(results.compareDocumentPosition(curve)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it('waits for both days of a range before reading the summary', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=range&from=2026-11-01' });

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(
      screen.getAllByText("Scegli l'inizio e la fine dell'intervallo.").length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole('region', { name: 'Riepilogo dei risultati' }),
    ).not.toBeInTheDocument();
  });

  it('keeps the badge of a draft apart from the notice of the test network, with the standard gap', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    const status = await screen.findByRole('group', { name: 'Stato del flusso' });
    const badge = within(status).getByText('Bozza');
    const notice = await within(status).findByText(/rete di test "sandbox"/);
    expect(status).toHaveClass(...STATUS_AND_NETWORK);
    expect(badge.className).not.toMatch(/\bm[trblxy]?-/);
    expect(notice.className).not.toMatch(/\bm[trblxy]?-/);
  });

  it('shows no summary for a draft, which has no account yet', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    fakePlatform.changeFlow('bozza', { accountId: null });
    await renderApp({ account: 'anna', url: '/flows/flow-bozza' });

    expect(await screen.findByText('Bozza')).toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Riepilogo dei risultati' }),
    ).not.toBeInTheDocument();
  });

  it('tells why the summary could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/state', () =>
        HttpResponse.json({ detail: 'exchange non raggiungibile, riprovare' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'exchange non raggiungibile, riprovare',
    );
  });

  it('tells why the flow could not be read', async () => {
    server.use(
      http.get('*/flows', () => HttpResponse.json({ detail: 'errore interno' }, { status: 500 })),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });

  it('keeps showing the flow and its cycles when a rereading fails', async () => {
    fakePlatform.concludeCycle('alfa', new Date(2026, 10, 14, 9, 45, 0));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/cycles' });
    const cycles = await screen.findByRole('table', { name: 'Cicli' });
    await within(cycles).findByText(/09:45:00/);
    fakePlatform.stopApi();

    await userEvent.click(screen.getByRole('button', { name: 'Aggiorna' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Dati non aggiornati');
    expect(screen.getByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Cicli' })).toHaveTextContent('09:45:00');
  });

  it('keeps a long name of a model within the configuration, breaking it where it does not fit', async () => {
    fakePlatform.changeFlow('alfa', { model: 'openrouter/~deepseek/deepseek-flash-latest' });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/versions' });

    const configuration = await screen.findByLabelText('Configurazione', { exact: true });
    expect(configuration).toHaveClass('grid-cols-[max-content_minmax(0,1fr)]');
    expect(
      within(configuration).getByText('openrouter/~deepseek/deepseek-flash-latest'),
    ).toHaveClass('min-w-0', 'wrap-anywhere');
  });
  it('says the openings are suspended by an alarm of reconciliation on the account (R3.3.2)', async () => {
    fakeReconciliation.openAlarm(fakePlatform.accountOfFlow('alfa').id, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(
      await screen.findByText('aperture sospese: allarme di riconciliazione sul conto principale'),
    ).toHaveAttribute('role', 'status');
  });

  it('says nothing of the openings of a flow whose account has no alarm', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    expect(
      await screen.findByRole('region', { name: 'Riepilogo dei risultati' }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/aperture sospese/)).not.toBeInTheDocument();
  });

  it('says nothing of the openings when the state of the flow cannot be read', async () => {
    fakeReconciliation.openAlarm(fakePlatform.accountOfFlow('alfa').id, 1000, 980, new Date());
    fakePlatform.stopExchange();
    server.use(
      http.get('*/flows/:flowId/state', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Unavailable',
            status: 503,
            detail: 'exchange non raggiungibile',
          },
          { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findAllByText(/exchange non raggiungibile/)).not.toHaveLength(0);
    expect(screen.queryByText(/aperture sospese/)).not.toBeInTheDocument();
  });
});
