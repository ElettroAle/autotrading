import { render, screen, within } from '@testing-library/react';

import type { Decision } from '../utils/cycle-documents';

import { DecisionLabel } from './decision-label';

const OPENING: Decision = {
  asset: 'BTC',
  action: 'apri',
  reasoning: 'RSI in risalita',
  opening: { direction: 'short' },
};

const HOLDING: Decision = {
  asset: 'ETH',
  action: 'mantieni',
  reasoning: 'laterale',
  opening: null,
};

const renderInHeading = (decision: Decision) =>
  render(
    <h3>
      <DecisionLabel decision={decision} />
    </h3>,
  );

describe('DecisionLabel', () => {
  it('names a decision by action, direction of an opening and asset, each with its icon', () => {
    renderInHeading(OPENING);

    expect(screen.getByRole('heading')).toHaveTextContent(/^apri short BTC$/);
    expect(screen.getByRole('heading')).toHaveAccessibleName('apri short BTC');
    expect(
      within(screen.getByText('apri', { exact: true })).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'plus');
    expect(
      within(screen.getByText('short', { exact: true })).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'arrow-down');
  });

  it('names a decision that opens nothing by action and asset', () => {
    renderInHeading(HOLDING);

    expect(screen.getByRole('heading')).toHaveTextContent(/^mantieni ETH$/);
    expect(screen.getAllByRole('img', { hidden: true })).toHaveLength(1);
  });
});
