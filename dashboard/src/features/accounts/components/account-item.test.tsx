import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS_PAGE = '/accounts';
const ACCOUNT_ID = 'account-principale';
const BALANCE = 'Saldo (con risultato aperto)';

const itemOf = (name: string): Promise<HTMLElement> => screen.findByRole('article', { name });

const detail = (item: HTMLElement, term: string): HTMLElement =>
  within(item).getByLabelText(term, { selector: 'dd' });

const reconciliationState = (item: HTMLElement): Promise<HTMLElement> =>
  within(item).findByRole('status', { name: 'Stato della riconciliazione' });

// ADR elenco-dei-conti-e-pagina-del-conto: one compact element per account, leading to the page of the account.
describe('AccountItem', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'principale', allocatedCapital: 300 });
  });

  it('heads the element with the name of the account, a link to its page, and its network', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const item = await itemOf('principale');
    const title = within(item).getByRole('heading', { name: 'principale' });
    expect(within(title).getByRole('link', { name: 'principale' })).toHaveAttribute(
      'href',
      `/accounts/${ACCOUNT_ID}`,
    );
    expect(within(item).getByText('TEST · testnet')).toBeInTheDocument();
  });

  it('opens the page of the account when the account is touched', async () => {
    const { router } = await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    await userEvent.click(
      within(await itemOf('principale')).getByRole('link', { name: 'principale' }),
    );

    expect(router.state.location.pathname).toBe(`/accounts/${ACCOUNT_ID}`);
    expect(
      await screen.findByRole('heading', { level: 1, name: 'principale' }),
    ).toBeInTheDocument();
  });

  it('shows the balance and the free capital, and nothing else of the account', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const item = await itemOf('principale');
    await waitFor(() => expect(detail(item, BALANCE)).toHaveTextContent('1000 USDC'));
    await waitFor(() => expect(detail(item, 'Capitale libero')).toHaveTextContent('700 USDC'));
    expect(
      within(item)
        .getAllByRole('term')
        .map((term) => term.textContent),
    ).toEqual([BALANCE, 'Capitale libero']);
    expect(within(item).queryByRole('region')).not.toBeInTheDocument();
    expect(within(item).queryByRole('table')).not.toBeInTheDocument();
  });

  it('says when the exchange does not answer', async () => {
    fakePlatform.stopExchange();
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const item = await itemOf('principale');
    expect(await within(item).findByText('Saldo non disponibile')).toBeInTheDocument();
    expect(await within(item).findByText('Capitale libero non disponibile')).toBeInTheDocument();
  });

  it('says that the account is aligned, with an icon and a text', async () => {
    fakeReconciliation.compare(ACCOUNT_ID, 1000, 1000, new Date());
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const state = await reconciliationState(await itemOf('principale'));
    expect(state).toHaveTextContent('Riconciliazione: allineato');
    expect(within(state).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'circle-check',
    );
  });

  it('says that the account is in alarm, with an icon and a text', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const state = await reconciliationState(await itemOf('principale'));
    expect(state).toHaveTextContent('Riconciliazione: allarme');
    expect(within(state).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'circle-alert',
    );
  });

  it('has no state while the reconciliation cannot be read', async () => {
    server.use(
      http.get('*/accounts/:accountId/reconciliation', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const item = await itemOf('principale');
    await waitFor(() => expect(detail(item, BALANCE)).toHaveTextContent('1000 USDC'));
    expect(
      within(item).queryByRole('status', { name: 'Stato della riconciliazione' }),
    ).not.toBeInTheDocument();
  });

  it('offers its actions in the menu «Azioni»', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const item = await itemOf('principale');
    await userEvent.click(
      within(item).getByRole('button', { name: 'Azioni del conto principale' }),
    );

    expect(
      within(item)
        .getAllByRole('menuitem')
        .map((action) => action.textContent),
    ).toEqual(['Sostituisci le credenziali', 'Rimuovi']);
  });

  it('keeps the page of the accounts when an action is chosen', async () => {
    const { router } = await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });
    const item = await itemOf('principale');

    await userEvent.click(
      within(item).getByRole('button', { name: 'Azioni del conto principale' }),
    );
    await userEvent.click(within(item).getByRole('menuitem', { name: 'Rimuovi' }));

    expect(router.state.location.pathname).toBe(ACCOUNTS_PAGE);
    expect(within(item).getByRole('alertdialog')).toBeInTheDocument();
  });
});
