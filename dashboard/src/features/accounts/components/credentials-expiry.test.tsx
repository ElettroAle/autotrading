import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const ACCOUNTS = '/accounts';
const ACCOUNT_PAGE = '/accounts/account-principale';
const TODAY = new Date('2026-11-15T06:00:00Z');

const notice = () => screen.queryByRole('region', { name: 'Chiavi da rinnovare' });

const expiryIn = (element: HTMLElement) => within(element).getByLabelText('Scadenza della chiave');

const overview = () => screen.findByRole('region', { name: 'Panoramica del conto principale' });

describe('the expiry of the credentials of the accounts (R6.2.2)', () => {
  beforeEach(() => {
    fakeClock.fix(TODAY);
  });

  it('shows in the list the expiry the exchange reads, as read', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiry = { expiresOn: '2026-12-30', source: 'read' };
    await renderApp({ account: 'anna', url: ACCOUNTS });

    const item = await screen.findByRole('article', { name: 'principale' });

    expect(expiryIn(item)).toHaveTextContent("scade il 30/12/2026 · letta dall'exchange");
    expect(notice()).not.toBeInTheDocument();
  });

  it('warns at the head of the list of the credentials that expire, with the way to replace them', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiry = { expiresOn: '2026-11-22', source: 'read' };
    await renderApp({ account: 'anna', url: ACCOUNTS });

    await screen.findByRole('article', { name: 'principale' });
    const warning = notice();
    expect(warning).toHaveTextContent('Chiave principale: scade tra 7 giorni');
    expect(
      within(warning as HTMLElement).getByRole('link', {
        name: 'Sostituisci le credenziali di principale',
      }),
    ).toHaveAttribute('href', '/accounts/account-principale/settings');
  });

  it('warns on the page of the account of credentials expired, and its overview shows them expired', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiry = { expiresOn: '2026-11-15', source: 'read' };
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    expect(expiryIn(await overview())).toHaveTextContent('scaduta · 15/11/2026');
    expect(notice()).toHaveTextContent('Chiave principale: scaduta');
    expect(screen.queryByRole('button', { name: 'Indica scadenza' })).not.toBeInTheDocument();
  });

  it('gives the expiry of credentials the exchange does not read', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiryEditable = true;
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });
    const card = await overview();
    expect(expiryIn(card)).toHaveTextContent('scadenza sconosciuta');

    await userEvent.click(within(card).getByRole('button', { name: 'Indica scadenza' }));
    await userEvent.type(within(card).getByLabelText('Scadenza'), '2027-03-15');
    await userEvent.click(within(card).getByRole('button', { name: 'Salva la scadenza' }));

    await waitFor(() => expect(expiryIn(card)).toHaveTextContent('scade il 15/03/2027'));
    expect(within(card).queryByLabelText('Scadenza')).not.toBeInTheDocument();
  });

  it('closes the date of the credentials without saving it', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiryEditable = true;
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });
    const card = await overview();

    await userEvent.click(within(card).getByRole('button', { name: 'Indica scadenza' }));
    await userEvent.click(within(card).getByRole('button', { name: 'Annulla' }));

    expect(within(card).queryByLabelText('Scadenza')).not.toBeInTheDocument();
    expect(account.expiry).toBeUndefined();
  });

  it('replaces credentials with the date of the new ones, and the warning goes', async () => {
    const account = fakePlatform.giveAccountTo('anna', 'principale', 1000);
    account.expiryEditable = true;
    account.expiry = { expiresOn: '2026-11-20', source: 'entered' };
    await renderApp({ account: 'anna', url: `${ACCOUNT_PAGE}/settings` });
    expect(await screen.findByRole('region', { name: 'Chiavi da rinnovare' })).toBeVisible();

    await userEvent.click(screen.getByRole('button', { name: 'Sostituisci le credenziali' }));
    await userEvent.type(await screen.findByLabelText("Chiave dell'API wallet"), '0xnuova');
    await userEvent.type(screen.getByLabelText('Scadenza'), '2027-03-15');
    await userEvent.click(screen.getByRole('button', { name: 'Sostituisci' }));

    await waitFor(() => expect(notice()).not.toBeInTheDocument());
    expect(account.expiry).toEqual({ expiresOn: '2027-03-15', source: 'entered' });
  });

  it('tells the exchange reads the expiry when the user gives one at the registration', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    await renderApp({ account: 'anna', url: ACCOUNTS });
    const region = await screen.findByRole('region', { name: 'Nuovo conto' });
    await within(region).findByRole('option', { name: 'Hyperliquid' });

    await userEvent.type(within(region).getByLabelText('Nome'), 'secondo');
    await userEvent.selectOptions(within(region).getByLabelText('Exchange'), 'Hyperliquid');
    await userEvent.type(within(region).getByLabelText('Indirizzo del conto'), '0xb2');
    await userEvent.type(within(region).getByLabelText("Chiave dell'API wallet"), '0xchiave');
    await userEvent.type(within(region).getByLabelText('Scadenza'), '2027-03-15');
    await userEvent.click(within(region).getByRole('button', { name: 'Registra il conto' }));

    expect(await within(region).findByRole('alert')).toHaveTextContent(
      "la scadenza di queste credenziali la legge l'exchange",
    );
  });
});
