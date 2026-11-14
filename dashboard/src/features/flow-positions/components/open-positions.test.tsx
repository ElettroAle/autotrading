import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const URL = '/flows/flow-alfa/positions';

const cellsOfFirstRow = async () => {
  const table = await screen.findByRole('table', { name: 'Posizioni aperte' });
  const [, first] = within(table).getAllByRole('row');
  return within(first as HTMLElement).getAllByRole('cell');
};

describe('OpenPositions', () => {
  beforeEach(() => {
    fakePlatform.giveFlowTo('anna', 'alfa');
  });

  it('shows asset, direction, size, leverage, entry, margin and PnL in value and percent', async () => {
    fakePlatform.holdPositions('alfa', [
      anOpenPosition({
        size: '0.01',
        leverage: '3',
        entryPrice: '60000',
        margin: '200',
        pnl: '12',
      }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    const cells = await cellsOfFirstRow();
    expect(cells.map((cell) => cell.textContent)).toEqual([
      'AssetBTC',
      'Direzionelong',
      'Dimensione0,01',
      'Leva3',
      'Prezzo di ingresso60.000',
      'Margine200 USDC',
      'PnL+12 USDC',
      'PnL %+6,00%',
    ]);
  });

  it('shows a gain in green and a loss in red', async () => {
    fakePlatform.holdPositions('alfa', [
      anOpenPosition({ asset: 'BTC', pnl: '12' }),
      anOpenPosition({ asset: 'ETH', side: 'short', pnl: '-4.5' }),
    ]);
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByText('+12 USDC')).toHaveClass('text-green-700');
    expect(screen.getByText('-4,5 USDC')).toHaveClass('text-red-700');
    expect(screen.getByText('-2,25%')).toHaveClass('text-red-700');
  });

  it('shows no percent for a position without margin', async () => {
    fakePlatform.holdPositions('alfa', [anOpenPosition({ margin: '0', pnl: '0' })]);
    await renderApp({ account: 'anna', url: URL });

    const cells = await cellsOfFirstRow();
    expect(cells.at(-1)).toHaveTextContent('PnL %—');
  });

  it('says the flow has no open position', async () => {
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByText('Nessuna posizione aperta.')).toBeInTheDocument();
  });

  it('tells why the positions could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/state', () =>
        HttpResponse.json({ detail: 'exchange non raggiungibile, riprovare' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: URL });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'exchange non raggiungibile, riprovare',
    );
  });
});
