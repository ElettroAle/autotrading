import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS_PAGE = '/accounts';

const rowOf = async (name: string): Promise<HTMLElement> => {
  const table = await screen.findByRole('table', { name: 'Conti' });
  const row = within(table)
    .getAllByRole('row')
    .find((candidate) => within(candidate).queryByRole('cell', { name }) !== null);
  if (row === undefined) {
    throw new Error(`no row for ${name}`);
  }
  return row;
};

describe('AccountsList', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'principale', allocatedCapital: 300 });
    fakePlatform.addFlow('anna', 'beta', { accountName: 'principale', allocatedCapital: 200 });
    fakePlatform.giveAccountTo('bruno', 'altrui', 50);
  });

  it('shows each account of the tenant with network, balance, allocated and free capital', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const row = await rowOf('principale');
    expect(within(row).getByText('testnet')).toBeInTheDocument();
    expect(await within(row).findByText('1000 USDC')).toBeInTheDocument();
    expect(within(row).getAllByText('500 USDC')).toHaveLength(2);
    expect(screen.queryByText('altrui')).not.toBeInTheDocument();
  });

  it.each([
    ['real', 'mainnet'],
    ['futura', 'futura'],
  ])('names the network %s as %s', async (network, label) => {
    server.use(
      http.get('*/accounts', () =>
        HttpResponse.json([
          {
            id: 'account-reale',
            name: 'reale',
            exchange: 'Hyperliquid',
            has_credentials: true,
            network,
            allocated_capital: '0',
            currency: 'USDC',
          },
        ]),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    expect(within(await rowOf('reale')).getByText(label)).toBeInTheDocument();
  });

  it('says there is no account yet and how to register one', async () => {
    fakePlatform.addUser('carla', { hasUserRole: true });
    await renderApp({ account: 'carla', url: ACCOUNTS_PAGE });

    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Registra il conto' })).toBeInTheDocument();
  });

  it('keeps network and allocated capital when the exchange does not answer', async () => {
    fakePlatform.stopExchange();
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const row = await rowOf('principale');
    expect(await within(row).findByText('Saldo non disponibile')).toBeInTheDocument();
    expect(await within(row).findByText('Capitale libero non disponibile')).toBeInTheDocument();
    expect(within(row).getByText('testnet')).toBeInTheDocument();
    expect(within(row).getByText('500 USDC')).toBeInTheDocument();
  });

  it('tells why the accounts could not be read', async () => {
    server.use(
      http.get('*/accounts', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });
});
