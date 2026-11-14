import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('AccountsRoute', () => {
  it('opens from the menu with the list and the form of registration', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('link', {
        name: 'Conti',
      }),
    );

    expect(router.state.location.pathname).toBe('/accounts');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi conti');
    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Nuovo conto' })).toBeVisible();
  });
});
