import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FAKE_IDENTITY_PROVIDER } from '@/testing/mocks/identity-provider';
import { renderApp } from '@/testing/test-utils';

const signInFrom = async (url: string) => {
  const { authClient } = await renderApp({ url });
  const loginRedirect = vi.spyOn(authClient, 'loginRedirect').mockResolvedValue();
  await userEvent.click(await screen.findByRole('button', { name: 'Accedi' }));
  return loginRedirect;
};

describe('LoginRoute', () => {
  it('invites the visitor to sign in with the account', async () => {
    await renderApp({ url: '/login' });

    expect(
      await screen.findByRole('heading', { name: 'Accesso alla dashboard' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('dev');
  });

  it('asks the identity provider for the scope of the API, returning to the page asked for', async () => {
    const loginRedirect = await signInFrom('/login?returnTo=%2Fflows%2Fflow-alfa');

    expect(loginRedirect).toHaveBeenCalledWith({
      scopes: [FAKE_IDENTITY_PROVIDER.scope],
      state: '/flows/flow-alfa',
    });
  });

  it('returns to the start page when no page was asked for', async () => {
    const loginRedirect = await signInFrom('/login');

    expect(loginRedirect).toHaveBeenCalledWith(expect.objectContaining({ state: '/' }));
  });

  it('never returns to an address outside the dashboard', async () => {
    const loginRedirect = await signInFrom('/login?returnTo=%2F%2Fexample.test');

    expect(loginRedirect).toHaveBeenCalledWith(expect.objectContaining({ state: '/' }));
  });
});
