import { render, screen, within } from '@testing-library/react';

import { Card } from './card';

// ADR card-condivisa-distinta-dallo-sfondo: every box of the dashboard is the shared card, filled with a colour of its
// own so that it stands apart from the background of the page, not only by its thin border.
describe('Card', () => {
  it('fills the box with white, apart from the background of the page', () => {
    render(<Card aria-label="Riquadro">contenuto</Card>);

    const card = screen.getByLabelText('Riquadro');
    expect(card).toHaveClass('bg-white', 'border', 'border-slate-200', 'p-4', 'shadow-sm');
    expect(card).not.toHaveClass('bg-slate-50');
  });

  it('keeps the colour of a box of error, still apart from the background', () => {
    render(
      <Card tone="error" aria-label="Errore">
        contenuto
      </Card>,
    );

    const card = screen.getByLabelText('Errore');
    expect(card).toHaveClass('bg-red-50', 'border-red-300');
    expect(card).not.toHaveClass('bg-white');
  });

  it('is a plain block unless the page names its element', () => {
    render(<Card data-testid="riquadro">contenuto</Card>);

    expect(screen.getByTestId('riquadro').tagName).toBe('DIV');
  });

  it('is the element the page names, with the attributes and the layout it gives', () => {
    render(
      <ul>
        <Card as="li" className="mt-4" data-testid="voce">
          contenuto
        </Card>
      </ul>,
    );

    const item = screen.getByRole('listitem');
    expect(item).toHaveClass('mt-4', 'bg-white');
    expect(item).toHaveAttribute('data-testid', 'voce');
  });

  it('is named by its title, with the description under it', () => {
    render(
      <Card as="article" title="indicatori" description="Indicatori tecnici">
        <p>contenuto</p>
      </Card>,
    );

    const card = screen.getByRole('article', { name: 'indicatori' });
    expect(within(card).getByRole('heading', { level: 2, name: 'indicatori' })).toBeVisible();
    expect(within(card).getByText('Indicatori tecnici')).toBeVisible();
    expect(within(card).getByText('contenuto')).toBeVisible();
  });

  it('has no heading without a title', () => {
    render(
      <Card as="section" aria-label="Senza titolo">
        contenuto
      </Card>,
    );

    const card = screen.getByRole('region', { name: 'Senza titolo' });
    expect(within(card).queryByRole('heading')).not.toBeInTheDocument();
  });

  it('shows a title without a description', () => {
    render(
      <Card as="section" title="Statistiche">
        contenuto
      </Card>,
    );

    const card = screen.getByRole('region', { name: 'Statistiche' });
    expect(within(card).getByRole('heading', { name: 'Statistiche' })).toBeVisible();
    expect(card).toHaveTextContent(/^Statistichecontenuto$/);
  });
});
