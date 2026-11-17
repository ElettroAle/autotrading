import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ExpandableText } from './expandable-text';

const SHORT = 'trend rialzista confermato';
const LONG = `${'momentum positivo sul timeframe orario con volumi in crescita '.repeat(4)}fine del ragionamento`;

// The text the command opens and closes, without the command.
const textOf = (command: HTMLElement): string =>
  screen.getByText((_, element) => element?.id === command.getAttribute('aria-controls'))
    .textContent ?? '';

// ADR-testo-lungo-espandibile (Bug 576): the long text opens in place with «Leggi tutto» and closes with «Riduci».
describe('ADR-testo-lungo-espandibile: ExpandableText', () => {
  it('shows a short text whole, without a command', () => {
    render(<ExpandableText text={SHORT} />);

    expect(screen.getByText(SHORT)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows a long text shortened, with «Leggi tutto» closed', () => {
    render(<ExpandableText text={LONG} />);

    const command = screen.getByRole('button', { name: 'Leggi tutto' });
    expect(command).toHaveAttribute('aria-expanded', 'false');
    expect(textOf(command).endsWith('…')).toBe(true);
    expect(textOf(command).length).toBeLessThanOrEqual(161);
    expect(LONG.startsWith(textOf(command).slice(0, -1))).toBe(true);
  });

  it('opens the whole text in place with «Leggi tutto»', async () => {
    render(<ExpandableText text={LONG} />);

    await userEvent.click(screen.getByRole('button', { name: 'Leggi tutto' }));

    const command = screen.getByRole('button', { name: 'Riduci' });
    expect(command).toHaveAttribute('aria-expanded', 'true');
    expect(textOf(command)).toBe(LONG);
  });

  it('closes the text again with «Riduci»', async () => {
    render(<ExpandableText text={LONG} />);
    await userEvent.click(screen.getByRole('button', { name: 'Leggi tutto' }));

    await userEvent.click(screen.getByRole('button', { name: 'Riduci' }));

    const command = screen.getByRole('button', { name: 'Leggi tutto' });
    expect(command).toHaveAttribute('aria-expanded', 'false');
    expect(textOf(command).endsWith('…')).toBe(true);
  });
});
