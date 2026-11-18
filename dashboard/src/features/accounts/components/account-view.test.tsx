import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp } from '@/testing/test-utils';

import { AccountView } from './account-view';

const TABS = 'le schede';

// ADR elenco-dei-conti-e-pagina-del-conto: the head of the page of the account, then its tabs, once it is read.
describe('AccountView', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('heads the tabs with the network of the account', async () => {
    await renderInApp(<AccountView accountId="account-principale">{TABS}</AccountView>, {
      account: 'anna',
    });

    const head = await screen.findByRole('region', { name: 'principale' });
    expect(head).toHaveTextContent('TEST · testnet');
    expect(screen.getByText(TABS)).toBeInTheDocument();
  });

  it('says when the user has no account with the id, without the tabs', async () => {
    await renderInApp(<AccountView accountId="account-omega">{TABS}</AccountView>, {
      account: 'anna',
    });

    expect(await screen.findByText('Conto non trovato.')).toBeInTheDocument();
    expect(screen.queryByText(TABS)).not.toBeInTheDocument();
  });

  it('tells why the accounts could not be read', async () => {
    server.use(
      http.get('*/accounts', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderInApp(<AccountView accountId="account-principale">{TABS}</AccountView>, {
      account: 'anna',
    });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
    expect(screen.queryByText(TABS)).not.toBeInTheDocument();
  });
});
