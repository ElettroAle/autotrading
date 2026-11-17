import { render, screen } from '@testing-library/react';

import { Icon, type IconName } from './icon';

const NAMES: readonly IconName[] = [
  'pause',
  'play',
  'square',
  'arrow-up',
  'arrow-down',
  'plus',
  'x',
  'refresh',
];

describe('Icon', () => {
  it.each(NAMES)('draws the icon %s, hidden from screen readers', (name) => {
    render(<Icon name={name} />);

    const drawing = screen.getByRole('img', { hidden: true });
    expect(drawing).toHaveAttribute('data-icon', name);
    expect(drawing).toHaveAttribute('aria-hidden', 'true');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('draws a different shape for each name', () => {
    render(
      <>
        {NAMES.map((name) => (
          <Icon key={name} name={name} />
        ))}
      </>,
    );

    const shapes = screen
      .getAllByRole('img', { hidden: true })
      .map((drawing) => drawing.getAttribute('class'));
    expect(new Set(shapes).size).toBe(NAMES.length);
  });
});
