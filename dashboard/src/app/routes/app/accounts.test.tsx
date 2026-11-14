import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('AccountsRoute', () => {
  it('opens from the home page with the list and the form of registration', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'I tuoi conti' }));

    expect(router.state.location.pathname).toBe('/accounts');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi conti');
    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Nuovo conto' })).toBeVisible();
  });
});
