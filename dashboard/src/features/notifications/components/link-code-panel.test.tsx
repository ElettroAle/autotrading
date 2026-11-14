import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform, FAKE_BOT_LINK, FAKE_LINK_CODE } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications';
const REQUEST_CODE = 'Chiedi il codice di collegamento';

describe('LinkCodePanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows the code the API issued, until when it is valid and the link of the bot', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: REQUEST_CODE }));

    expect(await screen.findByLabelText('Codice di collegamento')).toHaveTextContent(
      FAKE_LINK_CODE,
    );
    expect(screen.getByLabelText('Scadenza del codice')).toHaveAttribute(
      'datetime',
      fakePlatform.linkCodeOf('anna')?.expiresAt,
    );
    expect(screen.getByRole('link', { name: 'Apri il bot e collega la chat' })).toHaveAttribute(
      'href',
      `${FAKE_BOT_LINK}${FAKE_LINK_CODE}`,
    );
  });

  it('tells to send the code by hand while the bot is not active', async () => {
    server.use(
      http.post('*/telegram/link-code', () =>
        HttpResponse.json(
          { code: 'ABCD2345', expires_at: '2026-11-14T10:15:00Z', link: null },
          { status: 201 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: REQUEST_CODE }));

    expect(await screen.findByLabelText('Codice di collegamento')).toHaveTextContent('ABCD2345');
    expect(
      screen.getByText('Invia il codice al bot della piattaforma dalla tua chat Telegram.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Apri il bot e collega la chat' })).toBeNull();
  });

  it('tells why the code could not be issued', async () => {
    server.use(
      http.post('*/telegram/link-code', () =>
        HttpResponse.json({ detail: 'database non raggiungibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(await screen.findByRole('button', { name: REQUEST_CODE }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: database non raggiungibile',
    );
  });
});
