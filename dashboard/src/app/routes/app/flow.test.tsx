import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { partsAfter, renderApp } from '@/testing/test-utils';

// ADR zona-di-emergenza-in-fondo-alla-pagina: the emergency closing of the flow stands alone in the zone at the bottom
// of the page, away from the commands of the flow.
const ZONE = 'Zona di emergenza';
const EMERGENCY = /Chiusura di emergenza/;

describe('FlowRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('keeps the emergency closing of the flow alone in the zone at the bottom of the page', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const zone = await screen.findByRole('region', { name: ZONE });
    expect(
      within(zone)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Chiusura di emergenza del flusso alfa']);
    await screen.findByRole('navigation', { name: 'Dati del flusso' });
    expect(partsAfter(zone)).toEqual([]);
  });

  it('keeps the emergency closing out of the commands of the flow', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const head = await screen.findByRole('region', { name: 'alfa' });
    await within(head).findByRole('group', { name: 'Comandi del flusso' });
    expect(within(head).queryByRole('button', { name: EMERGENCY })).toBeNull();
  });

  it('has no zone for a draft, which holds no position', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    await renderApp({ account: 'anna', url: '/flows/flow-bozza' });

    await screen.findByText('Bozza');
    expect(screen.queryByRole('region', { name: ZONE })).toBeNull();
  });

  it('has no zone for a flow that does not exist', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega' });

    await screen.findByText('Flusso non trovato.');
    expect(screen.queryByRole('region', { name: ZONE })).toBeNull();
  });
});
