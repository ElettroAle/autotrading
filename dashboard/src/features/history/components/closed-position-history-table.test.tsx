import { render, screen } from '@testing-library/react';

import type { HistoryPosition } from '../api/get-closed-position-history';

import { ClosedPositionHistoryTable } from './closed-position-history-table';

const position = (pnl: string): HistoryPosition => ({
  id: `position-${pnl}`,
  flow: 'alfa',
  asset: 'BTC',
  side: 'long',
  leverage: 3,
  open_price: '100',
  close_price: '110',
  closed_at: '2026-11-18T10:00:00Z',
  pnl,
  pnl_percent_of_margin: '0',
  fees: '0.1',
  reason: 'agente',
});

const pnlOf = (pnl: string) =>
  screen.getByText(
    (_, element) => element?.tagName === 'SPAN' && element.textContent?.startsWith(pnl) === true,
  );

describe('ClosedPositionHistoryTable', () => {
  it('colours the PnL as every result of the dashboard: gain green, loss red, even grey (R2.2.2)', () => {
    render(
      <ClosedPositionHistoryTable positions={[position('12'), position('-3'), position('0')]} />,
    );

    expect(pnlOf('+12')).toHaveClass('text-green-700');
    expect(pnlOf('-3')).toHaveClass('text-red-700');
    expect(pnlOf('0 ')).toHaveClass('text-slate-700');
  });
});
