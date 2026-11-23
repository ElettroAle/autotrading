import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FAKE_EXCHANGE, fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

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
    ['the configuration of a flow', '/flows/flow-alfa/settings'],
    ['the editor of a flow', '/flows/new'],
  ])('shows the allocated capital after %s', async (_page, url) => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url });
    await screen.findAllByText('principale');

    await openAccountsFromTheMenu();

    const item = await within(await screen.findByRole('region', { name: 'Conti' })).findByRole(
      'article',
      { name: 'principale' },
    );
    // The capital allocated is on the overview of the page of the account (ADR elenco-dei-conti-e-pagina-del-conto).
    await userEvent.click(within(item).getByRole('link', { name: 'principale' }));
    const overview = await screen.findByRole('region', { name: 'Panoramica del conto principale' });
    expect(within(overview).getByLabelText('capitale allocato', { selector: 'dd' })).toBeVisible();
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

  // ADR zona-di-emergenza-nella-pagina-del-conto: the emergency closing of an account is on its page, not in the list.
  it('offers no emergency command', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addAccount('anna', 'test-1');
    fakePlatform.addAccount('anna', 'test-2');
    await renderApp({ account: 'anna', url: '/accounts' });

    await within(await screen.findByRole('region', { name: 'Conti' })).findByRole('article', {
      name: 'test-2',
    });
    expect(screen.queryByRole('button', { name: /Chiusura di emergenza/ })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Zona di emergenza' })).toBeNull();
  });
});
