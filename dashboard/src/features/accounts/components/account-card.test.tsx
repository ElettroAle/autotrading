import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { FAKE_ACCOUNT_ADDRESS, fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS_PAGE = '/accounts';
const ACCOUNT_ID = 'account-principale';

const cardOf = (name: string): Promise<HTMLElement> => screen.findByRole('article', { name });

const detail = (card: HTMLElement, term: string): HTMLElement =>
  within(card).getByLabelText(term, { selector: 'dd' });

const BALANCE = 'Saldo (con risultato aperto)';

const TOP_TERMS = [BALANCE, 'Valore dei flussi', 'Capitale libero'];

const reconciliationState = (card: HTMLElement): Promise<HTMLElement> =>
  within(card).findByRole('status', { name: 'Stato della riconciliazione' });

describe('AccountCard', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'principale', allocatedCapital: 300 });
    fakePlatform.addFlow('anna', 'beta', { accountName: 'principale', allocatedCapital: 200 });
  });

  it('heads the box with the name and the network of the account', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    const [title] = within(card).getAllByRole('heading');
    expect(title).toHaveTextContent('principale');
    expect(within(card).getByText('TEST · testnet')).toBeInTheDocument();
  });

  it('shows balance, value of the flows with the capital allocated to them, and free capital', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    await waitFor(() => expect(detail(card, BALANCE)).toHaveTextContent('1000 USDC'));
    expect(detail(card, 'capitale allocato')).toHaveTextContent('500');
    await waitFor(() => expect(detail(card, 'Capitale libero')).toHaveTextContent('500 USDC'));
  });

  describe('when the flows of the account are in gain (Bug 601)', () => {
    beforeEach(() => {
      server.use(
        http.get('*/accounts/:accountId/free-capital', () =>
          HttpResponse.json({
            amount: '704.561404',
            currency: 'USDC',
            flows_value: '308.927573',
            flows_result: '8.927573',
          }),
        ),
      );
    });

    it('breaks the balance down into the value of the flows and the free capital, in this order', async () => {
      await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

      const card = await cardOf('principale');
      await waitFor(() =>
        expect(detail(card, 'Valore dei flussi')).toHaveTextContent(/^308,927573 USDC/),
      );
      expect(detail(card, 'Capitale libero')).toHaveTextContent('704,561404 USDC');
      const terms = within(card)
        .getAllByRole('term')
        .map((term) => term.textContent);
      expect(terms.filter((term) => TOP_TERMS.includes(term ?? ''))).toEqual(TOP_TERMS);
    });

    it('says under the value of the flows the capital allocated plus their result', async () => {
      await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

      const card = await cardOf('principale');
      const value = detail(card, 'Valore dei flussi');
      await waitFor(() => expect(detail(value, 'risultato')).toHaveTextContent('+8,927573'));
      expect(value).toHaveTextContent('capitale allocato 500 + risultato +8,927573');
    });

    it('colours the result of the flows as a gain', async () => {
      await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

      const card = await cardOf('principale');
      await waitFor(() => expect(detail(card, 'risultato')).toHaveTextContent('+8,927573'));
      expect(detail(card, 'risultato')).toHaveClass('text-green-700');
    });
  });

  it.each([
    ['-5.5', '-5,5', 'text-red-700'],
    ['0', '0', 'text-slate-700'],
  ])('shows a result of the flows of %s with its sign and colour', async (result, text, tone) => {
    server.use(
      http.get('*/accounts/:accountId/free-capital', () =>
        HttpResponse.json({
          amount: '505.5',
          currency: 'USDC',
          flows_value: '494.5',
          flows_result: result,
        }),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    await waitFor(() => expect(detail(card, 'risultato')).toHaveTextContent(text));
    expect(detail(card, 'risultato')).toHaveClass(tone);
  });

  it('shows the public fields of the account with the labels the exchange gives them (Bug 401)', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const onExchange = detail(await cardOf('principale'), "Conto sull'exchange");
    expect(await within(onExchange).findByText('Indirizzo del conto')).toBeInTheDocument();
    expect(within(onExchange).getByText(FAKE_ACCOUNT_ADDRESS)).toBeInTheDocument();
  });

  it.each([
    ['real', 'REALE · sandbox'],
    ['test', 'TEST · sandbox'],
  ])('marks the network %s with the name the API gives it', async (network, label) => {
    server.use(
      http.get('*/accounts', () =>
        HttpResponse.json([
          {
            id: 'account-reale',
            name: 'reale',
            exchange: 'Hyperliquid',
            has_credentials: true,
            public_fields: {},
            network,
            network_name: 'sandbox',
            allocated_capital: '0',
            currency: 'USDC',
          },
        ]),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('reale');
    expect(within(card).getByText(label)).toBeInTheDocument();
    expect(within(card).queryByLabelText("Conto sull'exchange")).not.toBeInTheDocument();
  });

  it('keeps network and allocated capital when the exchange does not answer', async () => {
    fakePlatform.stopExchange();
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    expect(await within(card).findByText('Saldo non disponibile')).toBeInTheDocument();
    expect(await within(card).findByText('Capitale libero non disponibile')).toBeInTheDocument();
    expect(within(card).getByText('Valore dei flussi non disponibile')).toBeInTheDocument();
    expect(within(card).getByText('TEST · testnet')).toBeInTheDocument();
    expect(detail(card, 'capitale allocato')).toHaveTextContent('500');
    expect(within(card).queryByLabelText('risultato')).not.toBeInTheDocument();
  });

  it('says in the header that the account is aligned, with an icon and a text', async () => {
    fakeReconciliation.compare(ACCOUNT_ID, 1000, 1000, new Date());
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const state = await reconciliationState(await cardOf('principale'));
    expect(state).toHaveTextContent('Riconciliazione: allineato');
    expect(within(state).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'circle-check',
    );
  });

  it('says in the header that the account is in alarm, with an icon and a text', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const state = await reconciliationState(await cardOf('principale'));
    expect(state).toHaveTextContent('Riconciliazione: allarme');
    expect(within(state).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'circle-alert',
    );
  });

  it('shows the section Riconciliazione with its commands, then the commands of the account', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    const section = await within(card).findByRole('region', {
      name: 'Riconciliazione del conto principale',
    });
    expect(within(section).getByRole('heading', { name: 'Riconciliazione' })).toBeInTheDocument();
    expect(
      await within(section).findByRole('button', { name: 'Ho verificato' }),
    ).toBeInTheDocument();
    expect(within(section).getByRole('link', { name: 'Allarmi' })).toBeInTheDocument();
    expect(within(section).getByRole('button', { name: 'Modifica la soglia' })).toBeInTheDocument();
    const commands = within(card).getByRole('group', { name: 'Comandi del conto principale' });
    expect(
      section.compareDocumentPosition(commands) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      within(commands).getByRole('link', { name: 'Storico del capitale' }),
    ).toBeInTheDocument();
  });

  it('has no state in the header while the reconciliation cannot be read', async () => {
    server.use(
      http.get('*/accounts/:accountId/reconciliation', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Error', status: 500, detail: 'errore interno' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const card = await cardOf('principale');
    expect(await within(card).findByText(/errore interno/)).toBeInTheDocument();
    expect(
      within(card).queryByRole('status', { name: 'Stato della riconciliazione' }),
    ).not.toBeInTheDocument();
  });
});
