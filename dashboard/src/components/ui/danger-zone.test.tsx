import { render, screen, within } from '@testing-library/react';

import { DangerZone } from './danger-zone';

// ADR zona-di-emergenza-in-fondo-alla-pagina: one box, shared by the pages, that holds only the emergency commands.
describe('DangerZone', () => {
  it('is a region named and titled «Zona di emergenza»', () => {
    render(
      <DangerZone>
        <button type="button">Chiusura di emergenza</button>
      </DangerZone>,
    );

    const zone = screen.getByRole('region', { name: 'Zona di emergenza' });
    expect(within(zone).getByRole('heading', { name: 'Zona di emergenza' })).toBeVisible();
  });

  it('holds only the commands it is given', () => {
    render(
      <DangerZone>
        <button type="button">Chiusura di emergenza del conto test-1</button>
        <button type="button">Chiusura di emergenza del conto test-2</button>
      </DangerZone>,
    );

    const zone = screen.getByRole('region', { name: 'Zona di emergenza' });
    expect(
      within(zone)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Chiusura di emergenza del conto test-1', 'Chiusura di emergenza del conto test-2']);
  });
});
