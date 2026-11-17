import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const MAIL_SERVER = {
  host: 'smtp.example.com',
  port: 587,
  security: 'STARTTLS',
  username: 'anna@example.com',
  sender: 'anna@example.com',
  password: 'password-per-le-app',
} as const;

const tab = (name: RegExp | string) => screen.findByRole('tab', { name });

const box = (name: string) => screen.getByRole('region', { name });

// ADR-pagina-notifiche-a-schede: the preferences by default, the channels in a tab of their own with the number still
// to configure, every channel in the same shape with its state at the top.
describe('NotificationsRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('opens from the menu on the channels while none is linked, both to configure', async () => {
    const { router } = await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('link', {
        name: 'Notifiche',
      }),
    );

    expect(router.state.location.pathname).toBe('/notifications');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Notifiche');
    expect(await tab('Canali (2)')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Preferenze' })).toHaveAttribute(
      'aria-selected',
      'false',
    );
    expect(within(box('Telegram')).getByLabelText('Stato di Telegram')).toHaveTextContent(
      'Da configurare',
    );
    expect(within(box('Email')).getByLabelText('Stato di Email')).toHaveTextContent(
      'Da configurare',
    );
    expect(await within(box('Telegram')).findByText('Nessuna chat collegata')).toBeVisible();
  });

  it('shows Telegram before Email, each with its state, icon and text', async () => {
    fakePlatform.linkChat('anna', 'chat-anna');
    fakePlatform.saveMailServer('anna', MAIL_SERVER);
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    await renderApp({ account: 'anna', url: '/notifications?tab=channels' });

    expect(await tab('Canali')).toHaveAttribute('aria-selected', 'true');
    const titles = screen
      .getAllByRole('heading', { level: 2 })
      .map((heading) => heading.textContent);
    expect(titles.indexOf('Email')).toBeGreaterThan(titles.indexOf('Telegram'));
    const telegram = within(box('Telegram')).getByLabelText('Stato di Telegram');
    expect(telegram).toHaveTextContent(`Collegato: chat ${fakePlatform.chatNamed('chat-anna').id}`);
    expect(within(telegram).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'circle-check',
    );
    expect(within(box('Email')).getByLabelText('Stato di Email')).toHaveTextContent(
      'Collegato: smtp.example.com · anna@example.com',
    );
  });

  it('opens on the preferences once a channel is linked, and «Configura» leads to the channels', async () => {
    fakePlatform.linkChat('anna', 'chat-anna');
    const { router } = await renderApp({ account: 'anna', url: '/notifications' });

    expect(await tab('Preferenze')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Canali (1)' })).toBeInTheDocument();
    const reminder = await screen.findByLabelText('Canali da configurare');
    expect(reminder).toHaveTextContent('email non indicata, server di posta non configurato');

    await userEvent.click(within(reminder).getByRole('link', { name: 'Configura' }));

    expect(router.state.location.search).toBe('?tab=channels');
    expect(await tab('Canali (1)')).toHaveAttribute('aria-selected', 'true');
    expect(box('Email')).toBeVisible();
  });

  it('keeps the chosen tab in the address', async () => {
    const { router } = await renderApp({ account: 'anna', url: '/notifications' });

    await userEvent.click(await tab('Preferenze'));

    expect(router.state.location.search).toBe('?tab=preferences');
    expect(await screen.findByRole('table', { name: 'Canali per tipo di evento' })).toBeVisible();
  });

  it('says why the page cannot tell the state of the channels', async () => {
    server.use(
      http.get('*/notifications/mail-server', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/notifications' });

    expect(
      await screen.findByText('Impossibile leggere i dati: errore interno'),
    ).toBeInTheDocument();
  });
});
