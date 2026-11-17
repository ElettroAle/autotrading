import { render, screen } from '@testing-library/react';

import { HistoryTotals } from './history-totals';

const totals = () => screen.getByLabelText('Totali della ricerca');

describe('HistoryTotals', () => {
  it('shows the PnL with its sign in green and the fees of the whole search', () => {
    render(<HistoryTotals pnl="600" fees="25.2" />);

    expect(screen.getAllByRole('term').map((term) => term.textContent)).toEqual([
      'Totale PnL',
      'Totale commissioni',
    ]);
    expect(screen.getAllByRole('definition').map((value) => value.textContent)).toEqual([
      '+600',
      '25,2',
    ]);
    expect(screen.getByText('+600')).toHaveClass('text-green-700');
  });

  it('shows a loss in red', () => {
    render(<HistoryTotals pnl="-4.5" fees="0.42" />);

    expect(screen.getByText('-4,5')).toHaveClass('text-red-700');
    expect(totals()).toHaveTextContent('Totale commissioni0,42');
  });

  it('shows an even result without colour', () => {
    render(<HistoryTotals pnl="0" fees="0" />);

    expect(screen.getAllByText('0')[0]).toHaveClass('text-slate-700');
  });

  it('shows only the fees when the history has no result, as the orders', () => {
    render(<HistoryTotals fees="33" />);

    expect(screen.queryByText('Totale PnL')).not.toBeInTheDocument();
    expect(totals()).toHaveTextContent('Totale commissioni33');
  });
});
