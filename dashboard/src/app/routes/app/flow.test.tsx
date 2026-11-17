import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

// ADR impostazioni-del-flusso-dall-ingranaggio: the page of the flow holds reading and the commands of every day; the
// emergency closing of the flow and Archivia are in its settings.
const EMERGENCY = /Chiusura di emergenza/;

describe('FlowRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it.each(['attivo', 'fermo', 'in pausa'])(
    'offers no emergency closing, no Archivia and no zone for a flow %s',
    async (status) => {
      fakePlatform.addFlow('anna', 'alfa', { status });
      await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

      const head = await screen.findByRole('region', { name: 'alfa' });
      await within(head).findByRole('group', { name: 'Comandi del flusso' });
      await screen.findByRole('navigation', { name: 'Dati del flusso' });
      expect(screen.queryByRole('button', { name: EMERGENCY })).toBeNull();
      expect(screen.queryByRole('button', { name: 'Archivia' })).toBeNull();
      expect(screen.queryByRole('region', { name: 'Zona di emergenza' })).toBeNull();
      expect(screen.queryByRole('region', { name: 'Zona pericolosa' })).toBeNull();
    },
  );

  it('offers no Archivia for a draft on its page', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    await renderApp({ account: 'anna', url: '/flows/flow-bozza' });

    await screen.findByText('Bozza');
    expect(screen.queryByRole('button', { name: 'Archivia' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Zona pericolosa' })).toBeNull();
  });
});
