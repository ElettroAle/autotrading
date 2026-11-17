import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform, type FakeMailServer } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications?tab=channels';
const PASSWORD = 'password-per-le-app';
const SAVED: FakeMailServer = {
  host: 'smtp.example.com',
  port: 587,
  security: 'STARTTLS',
  username: 'anna@example.com',
  sender: 'anna@example.com',
  password: PASSWORD,
};
const SUMMARY = 'smtp.example.com:587 · STARTTLS · anna@example.com · password salvata';

const form = () => screen.findByRole('form', { name: 'Server di posta' });

const summary = () => screen.findByLabelText('Server di posta salvato');

// ADR-pagina-notifiche-a-schede, ADR-server-di-posta-per-tenant: the form while the server is configured, then one
// line with Modifica and Rimuovi; the password never comes back.
describe('MailServerPanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('saves a new server and sums it up in one line without the password', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const fields = within(await form());

    expect(
      screen.getByText('Gmail: smtp.gmail.com · 587 · STARTTLS · password per le app'),
    ).toBeVisible();
    expect(fields.getByLabelText('Porta')).toHaveValue('587');
    expect(fields.getByLabelText('Sicurezza')).toHaveValue('STARTTLS');
    await userEvent.type(fields.getByLabelText('Server'), 'smtp.example.com');
    await userEvent.type(fields.getByLabelText('Utente'), 'anna@example.com');
    await userEvent.type(fields.getByLabelText('Password'), PASSWORD);
    await userEvent.click(fields.getByRole('button', { name: 'Salva il server' }));

    expect(await summary()).toHaveTextContent(SUMMARY);
    expect(screen.queryByRole('form', { name: 'Server di posta' })).toBeNull();
    expect(document.body).not.toHaveTextContent(PASSWORD);
    expect(fakePlatform.mailServerOf('anna')).toEqual(SAVED);
  });

  it('shows the refusal of the API at the head of the form', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const fields = within(await form());

    await userEvent.type(fields.getByLabelText('Server'), 'smtp.example.com');
    await userEvent.type(fields.getByLabelText('Utente'), 'anna@example.com');
    await userEvent.click(fields.getByRole('button', { name: 'Salva il server' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'password del server di posta mancante',
    );
    expect(fakePlatform.mailServerOf('anna')).toBeUndefined();
  });

  it('changes the port and the security keeping the saved password', async () => {
    fakePlatform.saveMailServer('anna', SAVED);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await summary();
    await userEvent.click(screen.getByRole('button', { name: 'Modifica' }));
    const fields = within(await form());
    expect(fields.getByLabelText('Server')).toHaveValue('smtp.example.com');
    const password = fields.getByLabelText('Password (vuota per conservare quella salvata)');
    expect(password).toHaveValue('');
    await userEvent.clear(fields.getByLabelText('Porta'));
    await userEvent.type(fields.getByLabelText('Porta'), '465');
    await userEvent.selectOptions(fields.getByLabelText('Sicurezza'), 'TLS');
    await userEvent.click(fields.getByRole('button', { name: 'Salva il server' }));

    expect(await summary()).toHaveTextContent(
      'smtp.example.com:465 · TLS · anna@example.com · password salvata',
    );
    expect(fakePlatform.mailServerOf('anna')).toEqual({ ...SAVED, port: 465, security: 'TLS' });
  });

  it('leaves a change without saving it', async () => {
    fakePlatform.saveMailServer('anna', SAVED);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await summary();
    await userEvent.click(screen.getByRole('button', { name: 'Modifica' }));
    await userEvent.click(within(await form()).getByRole('button', { name: 'Annulla' }));

    expect(await summary()).toHaveTextContent(SUMMARY);
  });

  it('removes the server after the confirmation, and keeps it when the user cancels', async () => {
    fakePlatform.saveMailServer('anna', SAVED);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await summary();
    await userEvent.click(screen.getByRole('button', { name: 'Rimuovi' }));
    await userEvent.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Annulla' }),
    );
    expect(fakePlatform.mailServerOf('anna')).toEqual(SAVED);

    await userEvent.click(screen.getByRole('button', { name: 'Rimuovi' }));
    const dialog = screen.getByRole('alertdialog', { name: 'Rimozione del server di posta' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Conferma la rimozione' }));

    expect(await form()).toBeVisible();
    expect(fakePlatform.mailServerOf('anna')).toBeUndefined();
    expect(await screen.findByText('Configura prima il server di posta')).toBeVisible();
  });
});
