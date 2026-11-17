import type { IPublicClientApplication } from '@azure/msal-browser';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { AuthProvider } from '@/lib/auth';
import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { authClientFor } from '@/testing/test-utils';

import { UserMenu } from './user-menu';

const renderMenu = async (account?: string) => {
  const client = await authClientFor(account);
  const queryClient = new QueryClient();
  queryClient.setQueryData(['flows'], ['alfa']);
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <>
          <UserMenu />
          <p>fuori dal menu</p>
        </>
      ),
    },
  ]);
  render(
    <AuthProvider client={client} scope={FAKE_IDENTITY_PROVIDER.scope}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </AuthProvider>,
  );
  return { client, queryClient };
};

const userButton = () => screen.getByRole('button', { name: 'anna' });

const signOutItem = () => screen.queryByRole('menuitem', { name: 'Esci' });

const stubLogout = (client: IPublicClientApplication) =>
  vi.spyOn(client, 'logoutRedirect').mockResolvedValue();

// ADR area-utente-in-alto-a-destra.
describe('UserMenu', () => {
  it('shows the name of the signed-in user, with the menu closed', async () => {
    await renderMenu('anna');

    expect(await screen.findByRole('button', { name: 'anna' })).toHaveAttribute(
      'aria-haspopup',
      'menu',
    );
    expect(userButton()).toHaveAttribute('aria-expanded', 'false');
    expect(signOutItem()).not.toBeInTheDocument();
  });

  it('shows nothing before the sign-in', async () => {
    await renderMenu();

    expect(screen.getByText('fuori dal menu')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('opens a menu that holds only «Esci», with the focus on it', async () => {
    await renderMenu('anna');

    await userEvent.click(await screen.findByRole('button', { name: 'anna' }));

    expect(userButton()).toHaveAttribute('aria-expanded', 'true');
    const menu = screen.getByRole('menu');
    expect(userButton()).toHaveAttribute('aria-controls', menu.id);
    expect(screen.getAllByRole('menuitem').map((item) => item.textContent)).toEqual(['Esci']);
    expect(signOutItem()).toHaveFocus();
  });

  it('opens and closes from the keyboard, giving the focus back to the name', async () => {
    await renderMenu('anna');
    (await screen.findByRole('button', { name: 'anna' })).focus();

    await userEvent.keyboard('{Enter}');

    expect(signOutItem()).toHaveFocus();

    await userEvent.keyboard('{Escape}');

    expect(signOutItem()).not.toBeInTheDocument();
    expect(userButton()).toHaveAttribute('aria-expanded', 'false');
    expect(userButton()).toHaveFocus();
  });

  it('closes with a second click on the name', async () => {
    await renderMenu('anna');
    await userEvent.click(await screen.findByRole('button', { name: 'anna' }));

    await userEvent.click(userButton());

    expect(signOutItem()).not.toBeInTheDocument();
  });

  it('closes with a click outside the menu', async () => {
    await renderMenu('anna');
    await userEvent.click(await screen.findByRole('button', { name: 'anna' }));

    await userEvent.click(screen.getByText('fuori dal menu'));

    expect(signOutItem()).not.toBeInTheDocument();
    expect(userButton()).toHaveAttribute('aria-expanded', 'false');
  });

  it('stays open with a click inside the menu', async () => {
    await renderMenu('anna');
    await userEvent.click(await screen.findByRole('button', { name: 'anna' }));

    await userEvent.click(screen.getByRole('menu'));

    expect(signOutItem()).toBeInTheDocument();
  });

  it('signs out from «Esci», forgetting the data of the user', async () => {
    const { client, queryClient } = await renderMenu('anna');
    const logout = stubLogout(client);
    await userEvent.click(await screen.findByRole('button', { name: 'anna' }));

    await userEvent.click(screen.getByRole('menuitem', { name: 'Esci' }));

    expect(queryClient.getQueryData(['flows'])).toBeUndefined();
    expect(logout).toHaveBeenCalledOnce();
  });

  it('cuts a long name on a phone instead of pushing the bar wider', async () => {
    await renderMenu('anna');

    expect(await screen.findByText('anna')).toHaveClass('truncate', 'max-w-28', 'md:max-w-48');
  });

  it('is large enough to be touched on a phone', async () => {
    await renderMenu('anna');

    expect(await screen.findByRole('button', { name: 'anna' })).toHaveClass('min-h-11', 'min-w-11');
  });
});
