import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import {
  alertTarget,
  fakeInbox,
  flowTarget,
  INBOX_PAGE_SIZE,
} from '@/testing/mocks/notification-inbox';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

const ACCOUNT = 'anna';
const MINUTE = 60_000;

const tenant = (): string => fakePlatform.user(ACCOUNT).tenantId;

const notify = (title: string, minutesAgo: number, targets = [flowTarget('flow-alfa')]) =>
  fakeInbox.notify(
    tenant(),
    { icon: '🔔', title, text: `Errore: ${title}`, targets },
    new Date(Date.now() - minutesAgo * MINUTE),
  );

const bell = () => screen.findByRole('button', { name: /^Notifiche,/ });

const openDashboard = async (url = '/') => {
  const view = await renderApp({ account: ACCOUNT, url });
  await bell();
  await untilEveryRequestIsAnswered();
  return view;
};

const openPanel = async () => {
  await userEvent.click(await bell());
  const panel = await screen.findByRole('dialog', { name: 'Notifiche' });
  await untilEveryRequestIsAnswered();
  return panel;
};

beforeEach(() => {
  fakePlatform.addUser(ACCOUNT, { hasUserRole: true });
});

// ADR campanello-delle-notifiche-nella-dashboard: the bell beside the name, with the unread notifications of the tenant.
describe('NotificationBell', () => {
  it('says how many notifications are unread, with a mark that does not rely on colour alone', async () => {
    notify('alfa: ciclo fallito', 2);
    notify('beta: ciclo fallito', 1);

    await openDashboard();

    const button = await screen.findByRole('button', { name: 'Notifiche, 2 non lette' });
    expect(within(button).getByTestId('unread-count')).toHaveTextContent('2');
    expect(button).toHaveClass('min-h-11', 'min-w-11');
  });

  it('shows no mark without unread notifications', async () => {
    await openDashboard();

    const button = await screen.findByRole('button', { name: 'Notifiche, 0 non lette' });
    expect(within(button).queryByTestId('unread-count')).toBeNull();
  });

  it('shows 99+ beyond ninety-nine unread notifications', async () => {
    Array.from({ length: 100 }, (_, index) => notify(`flusso-${index}: ciclo fallito`, index));

    await openDashboard();

    expect(within(await bell()).getByTestId('unread-count')).toHaveTextContent('99+');
  });

  it('lists the notifications newest first, with icon, title, text and instant, the unread ones marked', async () => {
    const read = notify('alfa: ciclo fallito', 2);
    fakeInbox.markRead(tenant(), read.id, new Date());
    notify('beta: posizione aperta', 1);
    await openDashboard();

    const panel = await openPanel();

    const [newest, older] = within(panel).getAllByRole('listitem');
    expect(newest).toHaveTextContent('beta: posizione aperta');
    expect(newest).toHaveTextContent('Errore: beta: posizione aperta');
    expect(newest).toHaveTextContent('🔔');
    expect(newest).toHaveTextContent(/\d{2}\/\d{2}\/\d{4}/);
    expect(within(newest as HTMLElement).getByText('non letta')).toBeInTheDocument();
    expect(older).toHaveTextContent('alfa: ciclo fallito');
    expect(within(older as HTMLElement).queryByText('non letta')).toBeNull();
  });

  it('says so when there is no notification', async () => {
    await openDashboard();

    const panel = await openPanel();

    expect(within(panel).getByText('Nessuna notifica')).toBeInTheDocument();
    expect(within(panel).queryByRole('button', { name: 'Segna tutte come lette' })).toBeNull();
  });

  it('leads a chosen notification to its first page and reads it', async () => {
    notify('alfa: in pausa', 1, [alertTarget('alert-1'), flowTarget('flow-alfa')]);
    const { router } = await openDashboard();
    const panel = await openPanel();

    await userEvent.click(within(panel).getByRole('button', { name: /alfa: in pausa/ }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/alerts/alert-1'));
    await waitFor(() => expect(fakeInbox.unreadCount(tenant())).toBe(0));
    expect(
      await screen.findByRole('button', { name: 'Notifiche, 0 non lette' }),
    ).toBeInTheDocument();
  });

  it('only reads a chosen notification that leads nowhere', async () => {
    notify('AutoTrading: prova delle notifiche', 1, []);
    const { router } = await openDashboard('/accounts');
    const panel = await openPanel();

    await userEvent.click(within(panel).getByRole('button', { name: /prova delle notifiche/ }));

    expect(
      await screen.findByRole('button', { name: 'Notifiche, 0 non lette' }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/accounts');
  });

  it('marks every notification read at once', async () => {
    notify('alfa: ciclo fallito', 2);
    notify('beta: ciclo fallito', 1);
    await openDashboard();
    const panel = await openPanel();

    await userEvent.click(within(panel).getByRole('button', { name: 'Segna tutte come lette' }));

    expect(
      await screen.findByRole('button', { name: 'Notifiche, 0 non lette' }),
    ).toBeInTheDocument();
    expect(fakeInbox.unreadCount(tenant())).toBe(0);
    await waitFor(() => expect(within(panel).queryByText('non letta')).toBeNull());
  });

  it('reads the next notifications on request', async () => {
    Array.from({ length: INBOX_PAGE_SIZE + 1 }, (_, index) =>
      notify(`flusso-${index}: ciclo fallito`, index),
    );
    await openDashboard();
    const panel = await openPanel();
    expect(within(panel).getAllByRole('listitem')).toHaveLength(INBOX_PAGE_SIZE);

    await userEvent.click(within(panel).getByRole('button', { name: 'Mostra altre' }));

    await waitFor(() =>
      expect(within(panel).getAllByRole('listitem')).toHaveLength(INBOX_PAGE_SIZE + 1),
    );
    expect(within(panel).queryByRole('button', { name: 'Mostra altre' })).toBeNull();
  });

  it('closes with Esc, giving the focus back to the bell', async () => {
    await openDashboard();
    await openPanel();

    await userEvent.keyboard('{Escape}');

    expect(screen.queryByRole('dialog', { name: 'Notifiche' })).toBeNull();
    expect(await bell()).toHaveFocus();
    expect(await bell()).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes with a click outside it, and stays open on a click inside it', async () => {
    await openDashboard();
    const panel = await openPanel();

    await userEvent.click(within(panel).getByText('Nessuna notifica'));
    expect(screen.getByRole('dialog', { name: 'Notifiche' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('heading', { level: 1 }));

    expect(screen.queryByRole('dialog', { name: 'Notifiche' })).toBeNull();
  });

  it('opens and closes from the bell itself', async () => {
    await openDashboard();
    const button = await bell();

    await userEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(button);

    expect(button).toHaveAttribute('aria-expanded', 'false');
    await untilEveryRequestIsAnswered();
  });

  it('says why the list could not be read', async () => {
    server.use(
      http.get('*/notifications/inbox', () =>
        HttpResponse.json(
          { title: 'Service Unavailable', status: 503, detail: 'notifiche non disponibili' },
          { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await openDashboard();

    const panel = await openPanel();

    expect(await within(panel).findByRole('alert')).toHaveTextContent('notifiche non disponibili');
  });
});
