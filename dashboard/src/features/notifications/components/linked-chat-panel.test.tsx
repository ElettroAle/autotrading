import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { TEST_NOTIFICATION } from '@/testing/mocks/handlers';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications';
const SEND_TEST = 'Invia notifica di prova';
const UNLINK = 'Scollega la chat';
const CONFIRM_UNLINK = 'Conferma lo scollegamento';

describe('LinkedChatPanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
  });

  it('shows the linked chat of the tenant of the user', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    fakePlatform.linkChat('bruno', 'bruno_tg');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByLabelText('Chat collegata')).toHaveTextContent(
      `Chat Telegram ${fakePlatform.chatNamed('anna_tg').id}`,
    );
  });

  it('says no chat is linked and offers neither the test nor the unlinking', async () => {
    fakePlatform.linkChat('bruno', 'bruno_tg');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByText('Nessuna chat collegata')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: SEND_TEST })).toBeNull();
    expect(screen.queryByRole('button', { name: UNLINK })).toBeNull();
  });

  it('sends a test notification to the linked chat and confirms it', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: SEND_TEST }));

    expect(await screen.findByText('Notifica di prova inviata')).toBeInTheDocument();
    expect(fakePlatform.chatNamed('anna_tg').received).toEqual([TEST_NOTIFICATION]);
  });

  it('tells why the test notification was not sent', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    server.use(
      http.post('*/telegram/test-notification', () =>
        HttpResponse.json({ detail: 'nessuna chat collegata' }, { status: 409 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: SEND_TEST }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: nessuna chat collegata',
    );
    expect(screen.queryByText('Notifica di prova inviata')).toBeNull();
  });

  it('unlinks the chat only once the user confirms', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: UNLINK }));
    expect(fakePlatform.linkedChatOf('anna')).toBeDefined();
    await userEvent.click(screen.getByRole('button', { name: CONFIRM_UNLINK }));

    expect(await screen.findByText('Nessuna chat collegata')).toBeInTheDocument();
    expect(fakePlatform.linkedChatOf('anna')).toBeUndefined();
  });

  it('keeps the chat when the user cancels the unlinking', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: UNLINK }));
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));

    expect(screen.queryByRole('button', { name: CONFIRM_UNLINK })).toBeNull();
    expect(screen.getByRole('button', { name: UNLINK })).toBeInTheDocument();
    expect(fakePlatform.linkedChatOf('anna')).toBeDefined();
  });

  it('tells why the chat could not be unlinked', async () => {
    fakePlatform.linkChat('anna', 'anna_tg');
    server.use(
      http.delete('*/telegram/chat', () =>
        HttpResponse.json({ detail: 'database non raggiungibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: UNLINK }));
    await userEvent.click(screen.getByRole('button', { name: CONFIRM_UNLINK }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: database non raggiungibile',
    );
    expect(screen.getByLabelText('Chat collegata')).toBeInTheDocument();
  });

  it('tells why the linked chat could not be read', async () => {
    server.use(
      http.get('*/telegram/chat', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: errore interno',
    );
  });
});
