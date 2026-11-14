import { MutationCache, QueryCache } from '@tanstack/react-query';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { REJECTED_SECRET_KEY, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS = '/accounts';
const ADDRESS = '0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1';
const SECRET_KEY = '0x5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e';
const SECRET_LABEL = "Chiave dell'API wallet";

const form = () => screen.getByRole('region', { name: 'Nuovo conto' });

const fillAndSend = async ({ name = 'principale', secretKey = SECRET_KEY } = {}) => {
  const region = await screen.findByRole('region', { name: 'Nuovo conto' });
  await userEvent.type(within(region).getByLabelText('Nome'), name);
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
    expect(within(form()).getByLabelText(SECRET_LABEL)).toHaveValue('');
    expect(within(form()).getByLabelText('Exchange')).toHaveValue('hyperliquid');
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

  it('asks for every field before sending anything', async () => {
    const sent = vi.fn();
    server.use(http.post('*/accounts', sent));
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });

    await userEvent.clear(within(region).getByLabelText('Exchange'));
    await userEvent.click(within(region).getByRole('button', { name: 'Registra il conto' }));

    for (const label of ['Nome', 'Exchange', 'Indirizzo del conto', SECRET_LABEL]) {
      expect(await within(region).findByLabelText(label)).toHaveAccessibleDescription(
        'Campo obbligatorio',
      );
    }
    expect(sent).not.toHaveBeenCalled();
  });
});
