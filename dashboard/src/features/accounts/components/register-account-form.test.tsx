import { MutationCache, QueryCache } from '@tanstack/react-query';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { FAKE_EXCHANGE, REJECTED_SECRET_KEY, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS = '/accounts';
const ADDRESS = '0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1';
const SECRET_KEY = '0x5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e';
const SECRET_LABEL = "Chiave dell'API wallet";

const form = () => screen.getByRole('region', { name: 'Nuovo conto' });

const chooseExchange = async (region: HTMLElement) => {
  await within(region).findByRole('option', { name: FAKE_EXCHANGE });
  await userEvent.selectOptions(within(region).getByLabelText('Exchange'), FAKE_EXCHANGE);
};

const fillAndSend = async ({ name = 'principale', secretKey = SECRET_KEY } = {}) => {
  const region = await screen.findByRole('region', { name: 'Nuovo conto' });
  await userEvent.type(within(region).getByLabelText('Nome'), name);
  await chooseExchange(region);
  await userEvent.type(within(region).getByLabelText('Indirizzo del conto'), ADDRESS);
  await userEvent.type(within(region).getByLabelText(SECRET_LABEL), secretKey);
  await userEvent.click(within(region).getByRole('button', { name: 'Registra il conto' }));
};

describe('RegisterAccountForm', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('registers the account, which joins the list, and empties the form', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await fillAndSend();

    expect(await within(form()).findByRole('status')).toHaveTextContent(
      'Conto principale registrato',
    );
    expect(await screen.findByRole('cell', { name: 'principale' })).toBeInTheDocument();
    expect(within(form()).getByLabelText('Nome')).toHaveValue('');
    expect(within(form()).getByLabelText('Exchange')).toHaveValue('');
    expect(within(form()).queryByLabelText(SECRET_LABEL)).not.toBeInTheDocument();
  });

  it('offers only the exchanges the API supports, none chosen at first', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    const exchange = within(region).getByRole('combobox', { name: 'Exchange' });
    expect(await within(exchange).findByRole('option', { name: FAKE_EXCHANGE })).toBeEnabled();
    expect(
      within(exchange)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Scegli un exchange', FAKE_EXCHANGE]);
    expect(exchange).toHaveValue('');
  });

  it('tells the list of the exchanges is not available and sends nothing', async () => {
    fakePlatform.stopListingExchanges();
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    expect(await within(region).findByRole('alert')).toHaveTextContent(
      'Impossibile leggere gli exchange supportati: errore interno',
    );
    expect(within(region).getByLabelText('Exchange')).toBeDisabled();
    expect(within(region).getByRole('button', { name: 'Registra il conto' })).toBeDisabled();
  });

  it('leaves the credentials neither in the page nor in the cache of the data', async () => {
    const mutations = vi.spyOn(MutationCache.prototype, 'build');
    const queries = vi.spyOn(QueryCache.prototype, 'build');
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await fillAndSend();

    await screen.findByRole('cell', { name: 'principale' });
    expect(document.body.innerHTML).not.toContain(SECRET_KEY);
    const mutationCache = mutations.mock.contexts[0] as MutationCache;
    await waitFor(() => expect(mutationCache.getAll()).toEqual([]));
    const queryCache = queries.mock.contexts[0] as QueryCache;
    expect(JSON.stringify(queryCache.getAll().map((query) => query.state.data))).not.toContain(
      SECRET_KEY,
    );
  });

  it('shows the reason of the refusal at the head of the form and keeps the account out', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await fillAndSend({ name: 'rifiutato', secretKey: REJECTED_SECRET_KEY });

    expect(await within(form()).findByRole('alert')).toHaveTextContent(
      "credenziali rifiutate dall'exchange",
    );
    expect(within(form()).getByLabelText(SECRET_LABEL)).toHaveValue('');
    expect(within(form()).getByLabelText('Nome')).toHaveValue('rifiutato');
    expect(fakePlatform.user('anna').accounts.map(({ name }) => name)).not.toContain('rifiutato');
  });

  it('shows the reason beside the field the API names', async () => {
    server.use(
      http.post('*/accounts', () =>
        HttpResponse.json(
          {
            detail: 'richiesta non valida',
            errors: [{ loc: ['body', 'account_address'], msg: 'Input should be a valid string' }],
          },
          { status: 422 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await fillAndSend();

    expect(await within(form()).findByText('Input should be a valid string')).toBeInTheDocument();
    expect(within(form()).getByLabelText('Indirizzo del conto')).toHaveAccessibleDescription(
      'Input should be a valid string',
    );
  });

  it('asks for name and exchange before sending anything', async () => {
    const sent = vi.fn();
    server.use(http.post('*/accounts', sent));
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });
    await within(region).findByRole('option', { name: FAKE_EXCHANGE });

    await userEvent.click(within(region).getByRole('button', { name: 'Registra il conto' }));

    for (const label of ['Nome', 'Exchange']) {
      expect(await within(region).findByLabelText(label)).toHaveAccessibleDescription(
        'Campo obbligatorio',
      );
    }
    expect(sent).not.toHaveBeenCalled();
  });

  it('offers the exchanges the API lists and warns when the chosen one trades real money', async () => {
    fakePlatform.configureExchangeNetwork('real');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    expect(within(region).queryByRole('note')).not.toBeInTheDocument();
    await chooseExchange(region);

    expect(within(region).getByRole('note')).toHaveTextContent('Il conto opererà con denaro reale');
  });

  it('asks only the fields the chosen exchange declares, the secret ones hidden while typed', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    expect(within(region).queryByLabelText('Indirizzo del conto')).not.toBeInTheDocument();
    await chooseExchange(region);

    expect(within(region).getByLabelText('Indirizzo del conto')).not.toHaveAttribute(
      'type',
      'password',
    );
    expect(within(region).getByLabelText(SECRET_LABEL)).toHaveAttribute('type', 'password');
  });

  it('shows beside the declared field the reason the API gives when it is missing', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });
    await userEvent.type(within(region).getByLabelText('Nome'), 'principale');
    await chooseExchange(region);
    await userEvent.type(within(region).getByLabelText('Indirizzo del conto'), ADDRESS);

    await userEvent.click(within(region).getByRole('button', { name: 'Registra il conto' }));

    await waitFor(() =>
      expect(within(region).getByLabelText(SECRET_LABEL)).toHaveAccessibleDescription(
        "chiave dell'API wallet obbligatorio",
      ),
    );
    expect(fakePlatform.user('anna').accounts).toEqual([]);
  });

  it('warns that the chosen exchange trades on the test network the API names, without real money', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    await chooseExchange(region);

    expect(within(region).getByRole('note')).toHaveTextContent(
      'Il conto opererà sulla rete di test sandbox, senza denaro reale',
    );
  });
});
