import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { partsAfter, renderApp } from '@/testing/test-utils';

const COMMAND = 'Chiusura di emergenza di tutti i flussi';

// ADR voce-generale-con-la-zona-pericolosa: the settings of the platform, not of the user, with the emergency closing
// of every flow alone at the bottom, as in GitHub or Azure DevOps.
describe('GeneralSettingsRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('opens from the entry «Generale» of the settings in the menu', async () => {
    const { router } = await renderApp({ account: 'anna' });
    const settings = await screen.findByRole('list', { name: 'Impostazioni' });

    await userEvent.click(within(settings).getByRole('link', { name: 'Generale' }));

    expect(router.state.location.pathname).toBe('/settings/general');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Generale');
  });

  it('keeps the emergency closing of every flow alone in the zone at the bottom of the page', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: '/settings/general' });

    const zone = await screen.findByRole('region', { name: 'Zona di emergenza' });
    expect(
      within(zone)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual([COMMAND]);
    expect(partsAfter(zone)).toEqual([]);
  });

  it('asks the confirmation before closing every flow', async () => {
    fakePlatform.addFlow('anna', 'alfa', { assets: ['BTC'] });
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
    await renderApp({ account: 'anna', url: '/settings/general' });

    await userEvent.click(await screen.findByRole('button', { name: COMMAND }));

    expect(
      await screen.findByText('Chiudere 1 posizione di tutti i flussi e metterli in pausa?'),
    ).toBeInTheDocument();
  });
});
