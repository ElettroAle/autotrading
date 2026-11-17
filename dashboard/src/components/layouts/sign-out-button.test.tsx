import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { AuthProvider } from '@/lib/auth';
import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { authClientFor } from '@/testing/test-utils';

import { SignOutButton } from './sign-out-button';

const renderSignOut = async () => {
  const client = await authClientFor('anna');
  const queryClient = new QueryClient();
  queryClient.setQueryData(['flows'], ['alfa']);
  const router = createMemoryRouter([{ path: '/', element: <SignOutButton /> }]);
  render(
    <AuthProvider client={client} scope={FAKE_IDENTITY_PROVIDER.scope}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </AuthProvider>,
  );
  return { client, queryClient };
};

// ADR area-utente-in-alto-a-destra: «Esci» is the item of the menu of the user.
describe('SignOutButton', () => {
  it('forgets the data of the user and signs out at the identity provider', async () => {
    const { client, queryClient } = await renderSignOut();
    const logout = vi.spyOn(client, 'logoutRedirect').mockResolvedValue();

    await userEvent.click(screen.getByRole('menuitem', { name: 'Esci' }));

    expect(queryClient.getQueryData(['flows'])).toBeUndefined();
    expect(logout).toHaveBeenCalledOnce();
  });

  it('is large enough to be touched on a phone, as wide as the menu', async () => {
    await renderSignOut();

    expect(screen.getByRole('menuitem', { name: 'Esci' })).toHaveClass(
      'min-h-11',
      'min-w-11',
      'w-full',
    );
  });
});
