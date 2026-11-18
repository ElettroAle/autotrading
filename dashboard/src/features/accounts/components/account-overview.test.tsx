import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { FAKE_ACCOUNT_ADDRESS, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp, renderInApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

import { AccountOverview } from './account-overview';

// The overview is the tab the page of the account opens on (ADR elenco-dei-conti-e-pagina-del-conto).
const ACCOUNT_PAGE = '/accounts/account-principale';

const cardOf = (name: string): Promise<HTMLElement> =>
  screen.findByRole('region', { name: `Panoramica del conto ${name}` });

const detail = (card: HTMLElement, term: string): HTMLElement =>
  within(card).getByLabelText(term, { selector: 'dd' });

const BALANCE = 'Saldo (con risultato aperto)';

const TOP_TERMS = [BALANCE, 'Valore dei flussi', 'Capitale libero'];

describe('AccountOverview', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'principale', allocatedCapital: 300 });
    fakePlatform.addFlow('anna', 'beta', { accountName: 'principale', allocatedCapital: 200 });
  });

  it('shows balance, value of the flows with the capital allocated to them, and free capital', async () => {
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

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
      await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

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
      await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

      const card = await cardOf('principale');
      const value = detail(card, 'Valore dei flussi');
      await waitFor(() => expect(detail(value, 'risultato')).toHaveTextContent('+8,927573'));
      expect(value).toHaveTextContent('capitale allocato 500 + risultato +8,927573');
    });

    it('colours the result of the flows as a gain', async () => {
      await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

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
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    const card = await cardOf('principale');
    await waitFor(() => expect(detail(card, 'risultato')).toHaveTextContent(text));
    expect(detail(card, 'risultato')).toHaveClass(tone);
  });

  it('shows the public fields of the account with the labels the exchange gives them (Bug 401)', async () => {
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    const onExchange = detail(await cardOf('principale'), "Conto sull'exchange");
    expect(await within(onExchange).findByText('Indirizzo del conto')).toBeInTheDocument();
    expect(within(onExchange).getByText(FAKE_ACCOUNT_ADDRESS)).toBeInTheDocument();
  });

  it('has no row of the public fields for an account without them', async () => {
    fakePlatform.forgetPublicFieldsOf('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    const card = await cardOf('principale');
    expect(within(card).queryByLabelText("Conto sull'exchange")).not.toBeInTheDocument();
  });

  it('keeps the allocated capital when the exchange does not answer', async () => {
    fakePlatform.stopExchange();
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    const card = await cardOf('principale');
    expect(await within(card).findByText('Saldo non disponibile')).toBeInTheDocument();
    expect(await within(card).findByText('Capitale libero non disponibile')).toBeInTheDocument();
    expect(within(card).getByText('Valore dei flussi non disponibile')).toBeInTheDocument();
    expect(detail(card, 'capitale allocato')).toHaveTextContent('500');
    expect(within(card).queryByLabelText('risultato')).not.toBeInTheDocument();
  });

  it('shows nothing for an account the user does not have', async () => {
    await renderInApp(<AccountOverview accountId="account-omega" />, { account: 'anna' });

    await untilEveryRequestIsAnswered();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });
});
