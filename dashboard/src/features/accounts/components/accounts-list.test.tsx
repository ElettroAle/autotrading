import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS_PAGE = '/accounts';

const accountsList = (): Promise<HTMLElement> => screen.findByRole('region', { name: 'Conti' });

describe('AccountsList', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.giveAccountTo('anna', 'secondario', 10);
    fakePlatform.giveAccountTo('bruno', 'altrui', 50);
  });

  it('shows every account of the tenant in a box of its own (Bug 565)', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const list = await accountsList();
    // Every account comes from the same reading of the API: the boxes appear together.
    expect(await within(list).findAllByRole('article')).toHaveLength(2);
    expect(within(list).getByRole('article', { name: 'principale' })).toBeInTheDocument();
    expect(within(list).getByRole('article', { name: 'secondario' })).toBeInTheDocument();
    expect(screen.queryByText('altrui')).not.toBeInTheDocument();
  });

  it('lays the boxes in one column on a phone and two from a wide screen (Bug 565)', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    expect(await accountsList()).toHaveClass('grid', 'grid-cols-1', 'lg:grid-cols-2');
  });

  it('says there is no account yet and how to register one', async () => {
    fakePlatform.addUser('carla', { hasUserRole: true });
    await renderApp({ account: 'carla', url: ACCOUNTS_PAGE });

    expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Conti' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Registra il conto' })).toBeInTheDocument();
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
