import { render, screen, within } from '@testing-library/react';

import { ActionLabel } from './action-label';

describe('ActionLabel', () => {
  it.each([
    ['apri', 'plus'],
    ['chiudi', 'x'],
    ['mantieni', 'pause'],
    ['aggiorna', 'refresh'],
  ])('shows %s with its icon next to the text', (value, icon) => {
    render(<ActionLabel value={value} />);

    const label = screen.getByText(value, { exact: true });
    expect(within(label).getByRole('img', { hidden: true })).toHaveAttribute('data-icon', icon);
    expect(within(label).getByRole('img', { hidden: true })).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows an action it does not know as text alone', () => {
    render(<ActionLabel value="raddoppia" />);

    expect(
      within(screen.getByText('raddoppia', { exact: true })).queryByRole('img', { hidden: true }),
    ).toBeNull();
  });
});
