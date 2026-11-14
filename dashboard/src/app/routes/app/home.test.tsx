import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('HomeRoute', () => {
  it('leads to the accounts of the user', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'I tuoi conti' }));

    expect(router.state.location.pathname).toBe('/accounts');
    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
  });
});
