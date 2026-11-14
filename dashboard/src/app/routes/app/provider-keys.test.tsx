import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('ProviderKeysRoute', () => {
  it('opens from the menu as «Chiavi», with the section of the keys of the AI providers', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('link', {
        name: 'Chiavi',
      }),
    );

    expect(router.state.location.pathname).toBe('/provider-keys');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Chiavi');
    const section = screen.getByRole('region', { name: 'Chiavi dei fornitori IA' });
    expect(
      await within(section).findByText('Non hai ancora chiavi di fornitori IA.'),
    ).toBeInTheDocument();
    expect(within(section).getByRole('region', { name: 'Nuova chiave' })).toBeVisible();
  });
});
