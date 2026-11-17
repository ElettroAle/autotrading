import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import {
  MAIL_LOGIN_REFUSED,
  TEST_EMAIL_SUBJECT,
} from '@/testing/mocks/notification-email-handlers';
import { fakePlatform, type FakeMailServer } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications?tab=channels';
const MAIL_SERVER: FakeMailServer = {
  host: 'smtp.example.com',
  port: 587,
  security: 'STARTTLS',
  username: 'anna@example.com',
  sender: 'anna@example.com',
  password: 'password-per-le-app',
};
const ADDRESS = 'Indirizzo email';
const SAVE = 'Salva';
const REMOVE = 'Togli';
const SEND_TEST = 'Invia email di prova';

// ADR-indirizzo-email-nelle-impostazioni-delle-notifiche, ADR-pagina-notifiche-a-schede: the address, the second step
// of the email channel, its commands and the outcome of the test email.
describe('NotificationEmailPanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
    fakePlatform.saveMailServer('anna', MAIL_SERVER);
  });

  it('shows the address of the tenant of the user', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    fakePlatform.setNotificationEmail('bruno', 'bruno@example.com');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByLabelText('Indirizzo delle notifiche')).toHaveTextContent(
      'anna@example.com',
    );
    expect(screen.getByLabelText(ADDRESS)).toHaveValue('anna@example.com');
  });

  it('says no address is indicated and offers neither the test nor the removal', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByText('Nessun indirizzo email indicato')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: SEND_TEST })).toBeNull();
    expect(screen.queryByRole('button', { name: REMOVE })).toBeNull();
  });

  it('saves the address the user writes', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.type(await screen.findByLabelText(ADDRESS), 'anna@example.com');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    expect(await screen.findByLabelText('Indirizzo delle notifiche')).toHaveTextContent(
      'anna@example.com',
    );
    expect(fakePlatform.notificationEmailOf('anna')).toBe('anna@example.com');
  });

  it('shows the refusal of the API under the field and keeps the previous address', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const field = await screen.findByLabelText(ADDRESS);

    await userEvent.clear(field);
    await userEvent.type(field, 'anna@');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    expect(await screen.findByText('indirizzo email non valido')).toBeInTheDocument();
    expect(fakePlatform.notificationEmailOf('anna')).toBe('anna@example.com');
  });

  it('removes the address', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: REMOVE }));

    expect(await screen.findByText('Nessun indirizzo email indicato')).toBeInTheDocument();
    expect(fakePlatform.notificationEmailOf('anna')).toBeUndefined();
  });

  it('tells why the address was not removed', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    server.use(
      http.delete('*/notifications/email', () =>
        HttpResponse.json({ detail: 'servizio non disponibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: REMOVE }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: servizio non disponibile',
    );
  });

  it('sends a test email to the address and confirms it', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: SEND_TEST }));

    expect(await screen.findByText('Email di prova inviata')).toBeInTheDocument();
    expect(fakePlatform.emailsTo('anna@example.com')).toEqual([
      { to: 'anna@example.com', subject: TEST_EMAIL_SUBJECT, host: 'smtp.example.com' },
    ]);
  });

  it('shows beside the test the reason the mail server refused it', async () => {
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    fakePlatform.refuseMailLogin();
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: SEND_TEST }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      `Email di prova non inviata: ${MAIL_LOGIN_REFUSED}`,
    );
    expect(fakePlatform.emailsTo('anna@example.com')).toEqual([]);
  });

  it('waits for the mail server: the address cannot be saved and no test is offered', async () => {
    fakePlatform.removeMailServer('anna');
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByText('Configura prima il server di posta')).toBeInTheDocument();
    expect(screen.getByLabelText(ADDRESS)).toBeDisabled();
    expect(screen.getByRole('button', { name: SAVE })).toBeDisabled();
    expect(screen.queryByRole('button', { name: SEND_TEST })).toBeNull();
    expect(screen.getByRole('button', { name: REMOVE })).toBeEnabled();
  });

  it('tells why the address cannot be read', async () => {
    server.use(
      http.get('*/notifications/email', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(
      await screen.findByText('Impossibile leggere i dati: errore interno'),
    ).toBeInTheDocument();
  });
});
