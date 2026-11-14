import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('NotificationsRoute', () => {
  it('opens from the home page with the linked chat and the link code', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'Notifiche Telegram' }));

    expect(router.state.location.pathname).toBe('/notifications');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Notifiche Telegram');
    expect(await screen.findByText('Nessuna chat collegata')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chiedi il codice di collegamento' })).toBeVisible();
  });
});
