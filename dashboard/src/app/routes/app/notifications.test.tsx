import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('NotificationsRoute', () => {
  it('opens from the menu as «Notifiche», with the section of the Telegram notifications', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('link', {
        name: 'Notifiche',
      }),
    );

    expect(router.state.location.pathname).toBe('/notifications');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Notifiche');
    const section = screen.getByRole('region', { name: 'Notifiche Telegram' });
    expect(await within(section).findByText('Nessuna chat collegata')).toBeInTheDocument();
    expect(
      within(section).getByRole('button', { name: 'Chiedi il codice di collegamento' }),
    ).toBeVisible();
  });
});
