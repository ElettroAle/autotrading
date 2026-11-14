import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('ProviderKeysRoute', () => {
  it('opens from the home page with the list and the form of registration', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'Chiavi dei fornitori IA' }));

    expect(router.state.location.pathname).toBe('/provider-keys');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Chiavi dei fornitori IA');
    expect(await screen.findByText('Non hai ancora chiavi di fornitori IA.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Nuova chiave' })).toBeVisible();
  });
});
