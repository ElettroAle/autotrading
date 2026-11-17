import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { partsAfter, renderApp } from '@/testing/test-utils';

// ADR impostazioni-del-flusso-dall-ingranaggio: the settings of the flow, in order the configuration with its commands,
// the versions and, at the bottom, the zone of danger with the emergency closing of the flow and Archivia.
const ZONE = 'Zona pericolosa';
const SETTINGS = '/flows/flow-alfa/settings';

const zoneCommands = async (): Promise<string[]> =>
  within(await screen.findByRole('region', { name: ZONE }))
    .getAllByRole('button')
    .map((button) => button.textContent ?? '');

describe('FlowSettingsRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('titles the page with the settings of the flow', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: SETTINGS });

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Impostazioni di alfa' }),
    ).toBeInTheDocument();
  });

  it('shows the configuration with its commands, then the versions, then the zone at the bottom', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: SETTINGS });

    const edit = await screen.findByRole('link', { name: 'Modifica' });
    const configuration = screen.getByLabelText('Configurazione', { exact: true });
    const versions = await screen.findByRole('list', { name: 'Versioni' });
    const zone = await screen.findByRole('region', { name: ZONE });
    const order = [edit, configuration, versions, zone];
    order.slice(1).forEach((element, index) => {
      expect(order[index]?.compareDocumentPosition(element)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(screen.getByRole('button', { name: 'Duplica' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Esporta' })).toBeVisible();
    expect(partsAfter(zone)).toEqual([]);
  });

  it.each([
    ['attivo', ['Chiusura di emergenza del flusso alfa']],
    ['in pausa', ['Chiusura di emergenza del flusso alfa']],
    ['fermo', ['Chiusura di emergenza del flusso alfa', 'Archivia']],
  ])(
    'keeps in the zone of a flow %s the commands of danger it admits',
    async (status, commands) => {
      fakePlatform.addFlow('anna', 'alfa', { status });
      await renderApp({ account: 'anna', url: SETTINGS });

      expect(await zoneCommands()).toEqual(commands);
    },
  );

  it('keeps only Archivia in the zone of a draft, which holds no position', async () => {
    fakePlatform.addFlow('anna', 'alfa', { status: 'bozza', allocatedCapital: null });
    await renderApp({ account: 'anna', url: SETTINGS });

    expect(await zoneCommands()).toEqual(['Archivia']);
  });

  it('has no zone for a flow that does not exist', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega/settings' });

    await screen.findAllByText('Flusso non trovato.');
    expect(screen.queryByRole('region', { name: ZONE })).toBeNull();
  });

  it('leads from the old address of the versions to the settings, with its query', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    const { router } = await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/versions?first=1&second=2',
    });

    await screen.findByRole('heading', { level: 1, name: 'Impostazioni di alfa' });
    expect(router.state.location.pathname).toBe(SETTINGS);
    expect(router.state.location.search).toBe('?first=1&second=2');
  });
});
