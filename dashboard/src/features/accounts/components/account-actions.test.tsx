import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { REJECTED_SECRET_KEY, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS = '/accounts';
const ADDRESS = '0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1';
const SECRET_KEY = '0x7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c';
const SECRET_LABEL = "Chiave dell'API wallet";
const CONFIRM_REMOVAL = 'Conferma la rimozione';

const accountItem = async (name: string): Promise<HTMLElement> => {
  const table = await screen.findByRole('table', { name: 'Conti' });
  const row = within(table)
    .getAllByRole('row')
    .find((candidate) => within(candidate).queryByRole('cell', { name }) !== null);
  if (row === undefined) {
    throw new Error(`no row for ${name}`);
  }
  return row;
};

const accountNames = (account: string) =>
  fakePlatform.user(account).accounts.map(({ name }) => name);

const NO_ACCOUNT = 'Nessun conto registrato.';

const replaceCredentials = async (name: string, secretKey: string) => {
  const item = await accountItem(name);
  await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci le credenziali' }));
  await userEvent.type(within(item).getByLabelText('Indirizzo del conto'), ADDRESS);
  await userEvent.type(within(item).getByLabelText(SECRET_LABEL), secretKey);
  await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));
  return item;
};

const askRemoval = async (name: string) => {
  const item = await accountItem(name);
  await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
  const dialog = within(item).getByRole('alertdialog', { name: `Rimozione del conto ${name}` });
  await userEvent.click(within(dialog).getByRole('button', { name: CONFIRM_REMOVAL }));
  return item;
};

describe('AccountActions', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
    fakePlatform.addAccount('bruno', 'altrui');
  });

  it('replaces the credentials and confirms it, with the secret emptied', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });

    const item = await replaceCredentials('principale', SECRET_KEY);

    expect(await within(item).findByRole('status')).toHaveTextContent(
      'Credenziali del conto principale sostituite',
    );
    expect(within(item).queryByLabelText(SECRET_LABEL)).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(SECRET_KEY);
  });

  it('tells why the replacement was refused and empties the secret', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });

    const item = await replaceCredentials('principale', REJECTED_SECRET_KEY);

    expect(await within(item).findByRole('alert')).toHaveTextContent(
      "credenziali rifiutate dall'exchange",
    );
    expect(within(item).getByLabelText(SECRET_LABEL)).toHaveValue('');
  });

  it('asks for the credentials before sending the replacement, and can be cancelled', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const item = await accountItem('principale');

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci le credenziali' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByLabelText(SECRET_LABEL)).toHaveAccessibleDescription(
      'Campo obbligatorio',
    );
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));
    expect(within(item).queryByLabelText(SECRET_LABEL)).not.toBeInTheDocument();
  });

  it('removes an account without flows once the user confirms', async () => {
    fakePlatform.addAccount('anna', 'secondario');
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await askRemoval('secondario');

    expect(await screen.findByText(NO_ACCOUNT)).toBeInTheDocument();
    expect(accountNames('anna')).not.toContain('secondario');
  });

  it('says what happens to the flows of the account and removes it at the second confirmation', async () => {
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'principale' });
    await renderApp({ account: 'anna', url: ACCOUNTS });

    const item = await askRemoval('principale');

    const dialog = within(item).getByRole('alertdialog', {
      name: 'Rimozione del conto principale',
    });
    expect(
      await within(dialog).findByText(
        'il conto ha flussi attivi o in pausa che verranno fermati: alfa',
      ),
    ).toBeInTheDocument();
    expect(accountNames('anna')).toContain('principale');
    await userEvent.click(within(dialog).getByRole('button', { name: CONFIRM_REMOVAL }));
    expect(await screen.findByText(NO_ACCOUNT)).toBeInTheDocument();
  });

  it('tells why the removal failed', async () => {
    fakePlatform.addAccount('anna', 'principale');
    server.use(
      http.delete('*/accounts/:accountId', () =>
        HttpResponse.json({ detail: 'non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS });

    const item = await askRemoval('principale');

    expect(await within(item).findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: non trovato',
    );
  });

  it('keeps the account when the user cancels the removal', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const item = await accountItem('principale');

    await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));

    expect(within(item).queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(accountNames('anna')).toContain('principale');
  });
});
