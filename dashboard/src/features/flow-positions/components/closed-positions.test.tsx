import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { aClosedPosition } from '@/testing/mocks/positions';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const URL = '/flows/flow-alfa/closed-positions';
const LAST = new Date('2026-11-14T09:07:00Z');
const HOUR = 3_600_000;

const closedBack = (count: number) =>
  Array.from({ length: count }, (_, index) =>
    aClosedPosition({ closedAt: new Date(LAST.getTime() - index * HOUR) }),
  );

const rowsOf = async () => {
  const table = await screen.findByRole('table', { name: 'Posizioni chiuse' });
  return within(table).getAllByRole('row').slice(1);
};

describe('ClosedPositions', () => {
  beforeEach(() => {
    fakePlatform.giveFlowTo('anna', 'alfa');
  });

  it('shows the direction with its icon (R6.5.3)', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      aClosedPosition({ closedAt: LAST, side: 'short' }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    const [first] = await rowsOf();
    expect(
      within(within(first as HTMLElement).getByText('short')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'arrow-down');
  });

  it('shows every column of a closed position, from the most recent close', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      ...closedBack(2).slice(1),
      aClosedPosition({
        closedAt: LAST,
        asset: 'ETH',
        openPrice: '3000',
        closePrice: '3150',
        margin: '300',
        pnl: '15',
        fees: '0.12',
        reason: 'comando manuale',
      }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    await screen.findByText('+15 USDC');
    const [first] = await rowsOf();
    const cells = within(first as HTMLElement).getAllByRole('cell');
    expect(cells.map((cell) => cell.textContent)).toEqual([
      'AssetETH',
      'Direzionelong',
      'Aperta il14/11/2026, 09:07:00',
      'Apertura3000',
      'Chiusa il14/11/2026, 10:07:00',
      'Chiusura3150',
      'PnL+15 USDC',
      'PnL %+5,00%',
      'Commissioni0,12 USDC',
      'Motivocomando manuale',
    ]);
  });

  it('rounds the prices averaged over several fills (Bug 431)', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      aClosedPosition({
        closedAt: LAST,
        openPrice: '63996.0322580645161290322580',
        closePrice: '0.123456789',
      }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    const [first] = await rowsOf();
    expect(within(first as HTMLElement).getByText('63.996,03')).toBeInTheDocument();
    expect(within(first as HTMLElement).getByText('0,123457')).toBeInTheDocument();
  });

  it('shows a gain in green and a loss in red', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      aClosedPosition({ closedAt: LAST, pnl: '-2', margin: '100' }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByText('-2 USDC')).toHaveClass('text-red-700');
    expect(screen.getByText('-2,00%')).toHaveClass('text-red-700');
  });

  it('shows the amounts without currency when the exchange does not answer', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      aClosedPosition({ closedAt: LAST, pnl: '15', fees: '0.12' }),
    ]);
    let stateRefused = false;
    server.use(
      http.get('*/flows/:flowId/state', () => {
        stateRefused = true;
        return HttpResponse.json(
          { detail: 'exchange non raggiungibile, riprovare' },
          { status: 503 },
        );
      }),
    );
    await renderApp({ account: 'anna', url: URL });

    await waitFor(() => expect(stateRefused).toBe(true));
    const [first] = await rowsOf();
    const cells = within(first as HTMLElement).getAllByRole('cell');
    expect(cells.map((cell) => cell.textContent)).toEqual(
      expect.arrayContaining(['PnL+15', 'Commissioni0,12']),
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows 50 positions a page, with the next page and back', async () => {
    fakePlatform.recordClosedPositions('alfa', closedBack(60));
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: URL });

    expect(await rowsOf()).toHaveLength(50);
    await user.click(screen.getByRole('link', { name: 'Pagina successiva' }));

    await screen.findByText('Pagina 2');
    expect(await rowsOf()).toHaveLength(10);
    expect(screen.getByRole('link', { name: 'Pagina precedente' })).toHaveAttribute('href', URL);
  });

  it('says the flow has no closed position', async () => {
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByText('Nessuna posizione chiusa.')).toBeInTheDocument();
  });

  it('tells why the positions could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/closed-positions', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByRole('alert')).toHaveTextContent('flusso non trovato');
  });

  describe('with filters', () => {
    const SHORT_WON = { side: 'short', pnl: '3', fees: '0.1' };
    const LONG_LOST = { side: 'long', pnl: '-2', fees: '0.1' };

    it('shows only the lost positions, with how many they are', async () => {
      fakePlatform.recordClosedPositions('alfa', [
        aClosedPosition({ closedAt: LAST, ...SHORT_WON }),
        aClosedPosition({ closedAt: new Date(LAST.getTime() - HOUR), ...SHORT_WON }),
        aClosedPosition({ closedAt: new Date(LAST.getTime() - 2 * HOUR), ...LONG_LOST }),
      ]);
      const user = userEvent.setup();
      await renderApp({ account: 'anna', url: URL });
      expect(await screen.findByText('3 posizioni')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Perse' }));

      expect(await screen.findByText('1 posizione')).toBeInTheDocument();
      const [row] = await rowsOf();
      expect(row).toHaveTextContent('long');
    });

    it('offers the side, the result and the assets of the flow', async () => {
      fakePlatform.changeFlow('alfa', { assets: ['BTC', 'ETH'] });
      fakePlatform.recordClosedPositions('alfa', closedBack(1));
      await renderApp({ account: 'anna', url: `${URL}?side=short` });

      expect(await screen.findByRole('group', { name: 'Direzione' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Short' })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('group', { name: 'Risultato' })).toBeInTheDocument();
      const assets = screen.getByRole('group', { name: 'Asset' });
      expect(
        await within(assets)
          .findAllByRole('button')
          .then((buttons) => buttons.map((b) => b.textContent)),
      ).toEqual(['Tutti', 'BTC', 'ETH']);
    });

    it('shows the positions of one asset', async () => {
      fakePlatform.changeFlow('alfa', { assets: ['BTC', 'ETH'] });
      fakePlatform.recordClosedPositions('alfa', [
        aClosedPosition({ closedAt: LAST, asset: 'ETH' }),
        aClosedPosition({ closedAt: new Date(LAST.getTime() - HOUR) }),
      ]);
      const user = userEvent.setup();
      await renderApp({ account: 'anna', url: URL });

      await user.click(await screen.findByRole('button', { name: 'ETH' }));

      expect(await screen.findByText('1 posizione')).toBeInTheDocument();
      expect(await rowsOf()).toHaveLength(1);
    });
  });

  // ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune: the period of the page holds for the closed positions too.
  describe('in the period of the page, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune', () => {
    it('shows only the positions closed in the days of the period', async () => {
      fakePlatform.recordClosedPositions('alfa', closedBack(48));
      await renderApp({
        account: 'anna',
        url: `${URL}?period=range&from=2026-11-13T00:00Z&to=2026-11-13T22:59Z`,
      });

      const rows = await rowsOf();
      expect(rows.length).toBeGreaterThan(0);
      rows.forEach((row) => expect(row).toHaveTextContent('13/11/2026'));
    });

    it('says no position was closed in the period', async () => {
      fakePlatform.recordClosedPositions('alfa', closedBack(1));
      await renderApp({
        account: 'anna',
        url: `${URL}?period=range&from=2026-10-01T00:00Z&to=2026-10-02T23:59Z`,
      });

      expect(
        await screen.findByText('Nessuna posizione chiusa nel periodo scelto.'),
      ).toBeInTheDocument();
    });

    it('waits for both days of a range', async () => {
      await renderApp({ account: 'anna', url: `${URL}?period=range&to=2026-10-02T23:59Z` });

      expect(
        await screen.findByText("Scegli l'inizio e la fine dell'intervallo."),
      ).toBeInTheDocument();
    });
  });

  // ADR posizione-evidenziata-dall-indirizzo: the link of a notification points at the closing by asset and instant.
  describe('the position of the address', () => {
    const CLOSED_AT = encodeURIComponent('2026-11-14T09:07:00+00:00');

    it('highlights the row of the asset closed at the instant of the address', async () => {
      fakePlatform.recordClosedPositions('alfa', [
        aClosedPosition({ closedAt: LAST, asset: 'BTC' }),
        aClosedPosition({ closedAt: new Date(LAST.getTime() - HOUR), asset: 'ETH' }),
        aClosedPosition({ closedAt: LAST, asset: 'ETH' }),
      ]);
      await renderApp({ account: 'anna', url: `${URL}?asset=ETH&closed_at=${CLOSED_AT}` });

      const table = await screen.findByRole('table', { name: 'Posizioni chiuse' });
      const highlighted = within(table).getAllByRole('row', { current: true });
      expect(highlighted).toHaveLength(1);
      expect(
        within(highlighted[0] as HTMLElement).getByText('14/11/2026, 10:07:00'),
      ).toBeInTheDocument();
      expect(within(highlighted[0] as HTMLElement).getByText('Dalla notifica')).toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Cercala nello Storico' })).not.toBeInTheDocument();
    });

    it('leads to the history of the flow and the asset when the row is not on the page', async () => {
      fakePlatform.recordClosedPositions('alfa', [
        aClosedPosition({ closedAt: new Date(LAST.getTime() - HOUR), asset: 'ETH' }),
      ]);
      await renderApp({ account: 'anna', url: `${URL}?asset=ETH&closed_at=${CLOSED_AT}` });

      const table = await screen.findByRole('table', { name: 'Posizioni chiuse' });
      expect(within(table).queryByRole('row', { current: true })).not.toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent(
        "L'operazione della notifica non è in questa pagina.",
      );
      expect(screen.getByRole('link', { name: 'Cercala nello Storico' })).toHaveAttribute(
        'href',
        '/history?tab=closed-positions&flow=flow-alfa&asset=ETH',
      );
    });

    it('says nothing of a notification without the instant of a closing', async () => {
      fakePlatform.recordClosedPositions('alfa', [
        aClosedPosition({ closedAt: LAST, asset: 'ETH' }),
      ]);
      await renderApp({ account: 'anna', url: `${URL}?asset=ETH` });

      const table = await screen.findByRole('table', { name: 'Posizioni chiuse' });
      expect(within(table).queryByRole('row', { current: true })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Cercala nello Storico' })).not.toBeInTheDocument();
    });
  });
});
