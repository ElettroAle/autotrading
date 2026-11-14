import { screen, within } from '@testing-library/react';
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

    const [first] = await rowsOf();
    const cells = within(first as HTMLElement).getAllByRole('cell');
    expect(cells.map((cell) => cell.textContent)).toEqual([
      'AssetETH',
      'Direzionelong',
      'Aperta il14/11/2026, 09:07:00',
      'Apertura3000',
      'Chiusa il14/11/2026, 10:07:00',
      'Chiusura3150',
      'PnL+15',
      'PnL %+5,00%',
      'Commissioni0,12',
      'Motivocomando manuale',
    ]);
  });

  it('shows a gain in green and a loss in red', async () => {
    fakePlatform.recordClosedPositions('alfa', [
      aClosedPosition({ closedAt: LAST, pnl: '-2', margin: '100' }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByText('-2')).toHaveClass('text-red-700');
    expect(screen.getByText('-2,00%')).toHaveClass('text-red-700');
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
});
