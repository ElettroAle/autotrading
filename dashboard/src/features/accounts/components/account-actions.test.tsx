import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { FAKE_ACCOUNT_ADDRESS, REJECTED_SECRET_KEY, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS = '/accounts';
const ADDRESS = '0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1';
const SECRET_KEY = '0x7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c';
const SECRET_LABEL = "Chiave dell'API wallet";
const ADDRESS_LABEL = 'Indirizzo del conto';
const CONFIRM_REMOVAL = 'Conferma la rimozione';

// The element of the account in the list, with its menu «Azioni» (ADR elenco-dei-conti-e-pagina-del-conto).
const accountItem = (name: string): Promise<HTMLElement> => screen.findByRole('article', { name });

const chooseAction = async (item: HTMLElement, name: string, action: string) => {
  await userEvent.click(within(item).getByRole('button', { name: `Azioni del conto ${name}` }));
  await userEvent.click(within(item).getByRole('menuitem', { name: action }));
};

const accountNames = (account: string) =>
  fakePlatform.user(account).accounts.map(({ name }) => name);

const NO_ACCOUNT = 'Nessun conto registrato.';

const replaceCredentials = async (name: string, secretKey: string) => {
  const item = await accountItem(name);
  await chooseAction(item, name, 'Sostituisci le credenziali');
  await userEvent.type(within(item).getByLabelText(SECRET_LABEL), secretKey);
  await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));
  return item;
};

const askRemoval = async (name: string) => {
  const item = await accountItem(name);
  await chooseAction(item, name, 'Rimuovi');
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

    expect(
      await within(item).findByText('Credenziali del conto principale sostituite'),
    ).toHaveAttribute('role', 'status');
    expect(within(item).queryByLabelText(SECRET_LABEL)).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(SECRET_KEY);
  });

  it('asks only the secret fields and shows the public ones as registered (Bug 401)', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const item = await accountItem('principale');

    await chooseAction(item, 'principale', 'Sostituisci le credenziali');

    const form = within(item).getByRole('form', { name: 'Nuove credenziali del conto principale' });
    expect(within(form).queryByLabelText(ADDRESS_LABEL)).not.toBeInTheDocument();
    expect(within(form).getByText(FAKE_ACCOUNT_ADDRESS)).toBeInTheDocument();
    expect(within(form).getByLabelText(SECRET_LABEL)).toBeInTheDocument();
  });

  it('asks every field of an account registered without its public fields, and keeps them', async () => {
    fakePlatform.addAccount('anna', 'principale');
    fakePlatform.forgetPublicFieldsOf('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const item = await accountItem('principale');

    await chooseAction(item, 'principale', 'Sostituisci le credenziali');
    await userEvent.type(within(item).getByLabelText(ADDRESS_LABEL), ADDRESS);
    await userEvent.type(within(item).getByLabelText(SECRET_LABEL), SECRET_KEY);
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(
      await within(item).findByText('Credenziali del conto principale sostituite'),
    ).toHaveAttribute('role', 'status');
    expect(fakePlatform.accountNamed('principale').publicFields).toEqual(
      expect.objectContaining({ account_address: ADDRESS }),
    );
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

  it('tells beside the secret field it is missing when the replacement is sent empty, and can be cancelled', async () => {
    fakePlatform.addAccount('anna', 'principale');
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const item = await accountItem('principale');

    await chooseAction(item, 'principale', 'Sostituisci le credenziali');
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    await waitFor(() =>
      expect(within(item).getByLabelText(SECRET_LABEL)).toHaveAccessibleDescription(
        "chiave dell'API wallet obbligatorio",
      ),
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

    await chooseAction(item, 'principale', 'Rimuovi');
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));

    expect(within(item).queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(accountNames('anna')).toContain('principale');
  });
});
