import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FAKE_EXCHANGE, fakePlatform } from '@/testing/mocks/platform';
import { partsAfter, renderApp } from '@/testing/test-utils';

const openAccountsFromTheMenu = async () =>
  userEvent.click(
    within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('link', {
      name: 'Conti',
    }),
  );

describe('AccountsRoute', () => {
  it('opens from the menu with the list and the form of registration', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    const { router } = await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    await openAccountsFromTheMenu();

    expect(router.state.location.pathname).toBe('/accounts');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi conti');
    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Nuovo conto' })).toBeVisible();
  });

  // Bug 437: the flow page and the flow editor read the accounts with schemas of their own; the accounts page must not
  // receive their reduced accounts from the cache.
  it.each([
    ['the configuration of a flow', '/flows/flow-alfa/versions'],
    ['the editor of a flow', '/flows/new'],
  ])('shows the allocated capital after %s', async (_page, url) => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url });
    await screen.findAllByText('principale');

    await openAccountsFromTheMenu();

    const card = await within(await screen.findByRole('region', { name: 'Conti' })).findByRole(
      'article',
      { name: 'principale' },
    );
    expect(within(card).getByLabelText('Capitale allocato', { selector: 'dd' })).toBeVisible();
  });

  it('rereads the accounts of the flow editor after an account is registered', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addAccount('anna', 'principale');
    const { router } = await renderApp({ account: 'anna', url: '/flows/new' });
    await screen.findByRole('option', { name: 'principale' });
    await openAccountsFromTheMenu();

    const form = await screen.findByRole('region', { name: 'Nuovo conto' });
    await userEvent.type(within(form).getByLabelText('Nome'), 'secondario');
    await within(form).findByRole('option', { name: FAKE_EXCHANGE });
    await userEvent.selectOptions(within(form).getByLabelText('Exchange'), FAKE_EXCHANGE);
    await userEvent.type(
      within(form).getByLabelText('Indirizzo del conto'),
      '0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1',
    );
    await userEvent.type(
      within(form).getByLabelText("Chiave dell'API wallet"),
      '0x5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e',
    );
    await userEvent.click(within(form).getByRole('button', { name: 'Registra il conto' }));
    await within(form).findByRole('status');
    await act(() => router.navigate('/flows/new'));

    expect(await screen.findByRole('option', { name: 'secondario' })).toBeInTheDocument();
  });

  // ADR zona-di-emergenza-in-fondo-alla-pagina: one command per account, each naming it, in the zone after the form.
  it('keeps the emergency closing of each account in the zone at the bottom of the page', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addAccount('anna', 'test-1');
    fakePlatform.addAccount('anna', 'test-2');
    await renderApp({ account: 'anna', url: '/accounts' });

    const zone = await screen.findByRole('region', { name: 'Zona di emergenza' });
    expect(
      within(zone)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Chiusura di emergenza del conto test-1', 'Chiusura di emergenza del conto test-2']);
    expect(partsAfter(zone)).toEqual([]);
  });

  it('keeps the emergency closing out of the commands of the accounts', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addAccount('anna', 'test-1');
    await renderApp({ account: 'anna', url: '/accounts' });

    const list = await screen.findByRole('region', { name: 'Conti' });
    expect(within(list).queryByRole('button', { name: /Chiusura di emergenza/ })).toBeNull();
  });

  it('has no zone without an account', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    await renderApp({ account: 'anna', url: '/accounts' });

    await screen.findByText('Nessun conto registrato.');
    expect(screen.queryByRole('region', { name: 'Zona di emergenza' })).toBeNull();
  });
});
