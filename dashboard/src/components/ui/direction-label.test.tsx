import { render, screen, within } from '@testing-library/react';

import { DirectionLabel } from './direction-label';

describe('DirectionLabel', () => {
  it.each([
    ['long', 'arrow-up', 'text-green-700'],
    ['short', 'arrow-down', 'text-red-700'],
  ])('shows %s with its icon and colour next to the text', (value, icon, colour) => {
    render(<DirectionLabel value={value} />);

    const label = screen.getByText(value, { exact: true });
    expect(label).toHaveClass(colour);
    expect(within(label).getByRole('img', { hidden: true })).toHaveAttribute('data-icon', icon);
    expect(within(label).getByRole('img', { hidden: true })).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows a direction it does not know as text alone', () => {
    render(<DirectionLabel value="neutral" />);

    expect(
      within(screen.getByText('neutral', { exact: true })).queryByRole('img', { hidden: true }),
    ).toBeNull();
  });

  it('knows only the directions, not the properties of an object', () => {
    render(<DirectionLabel value="constructor" />);

    expect(
      within(screen.getByText('constructor', { exact: true })).queryByRole('img', { hidden: true }),
    ).toBeNull();
  });
});
