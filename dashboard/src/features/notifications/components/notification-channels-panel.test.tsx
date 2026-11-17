import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakeNotificationChannels } from '@/testing/mocks/notification-channels';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications?tab=preferences';
const GENERAL = 'Canali per tipo di evento';
const FAILED_CYCLE = 'ciclo fallito';
const OPENING = 'apertura di una posizione';
const REDUCED = 'decisione ridotta dal rischio';
const ALARM = 'allarme di riconciliazione';
const AS_GENERAL = 'Come la scelta generale';
const MAIL_SERVER = {
  host: 'smtp.example.com',
  port: 587,
  security: 'STARTTLS',
  username: 'anna',
  sender: 'anna@example.com',
  password: 'segreta',
} as const;

const generalTable = async () => screen.findByRole('table', { name: GENERAL });

const exceptionsTable = () => screen.findByRole('table', { name: 'Eccezioni di alfa' });

const rowOf = (table: HTMLElement, event: string): HTMLElement => {
  const row = within(table)
    .getAllByRole('row')
    .find((candidate) => within(candidate).queryByText(event) !== null);
  if (row === undefined) {
    throw new Error(`no row for ${event}`);
  }
  return row;
};

const switchOf = (table: HTMLElement, event: string, channel: string) =>
  within(rowOf(table, event)).getByRole('button', { name: channel });

const pressedOf = (table: HTMLElement, event: string): string[] =>
  within(rowOf(table, event))
    .getAllByRole('button', { pressed: true })
    .map((button) => button.textContent ?? '');

const chooseFlowAlfa = async () => {
  await userEvent.selectOptions(await screen.findByLabelText('Flusso'), 'alfa');
};

// ADR-interruttori-dei-canali-nelle-preferenze: one switch per channel of the API in the row of every event, a channel
// not configured disabled with its reason and «Configura», the exceptions of a flow with the same switches.
describe('NotificationChannelsPanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.linkChat('anna', 'chat-anna');
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
    fakePlatform.saveMailServer('anna', MAIL_SERVER);
  });

  it('shows a switch for every channel of the API in the row of every event, on for its channels', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const table = await generalTable();

    expect(pressedOf(table, OPENING)).toEqual(['Telegram']);
    expect(switchOf(table, OPENING, 'email')).toHaveAttribute('aria-pressed', 'false');
    expect(within(rowOf(table, REDUCED)).queryAllByRole('button', { pressed: true })).toEqual([]);
    expect(pressedOf(table, ALARM)).toEqual(['Telegram']);
    expect(
      within(rowOf(table, OPENING)).getByRole('group', { name: `Canali di ${OPENING}` }),
    ).toBeInTheDocument();
  });

  it('turns a channel on and saves the channels of the event', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(switchOf(await generalTable(), FAILED_CYCLE, 'email'));

    await waitFor(() => {
      expect(fakeNotificationChannels.channelsOf('anna', FAILED_CYCLE)).toEqual([
        'Telegram',
        'email',
      ]);
    });
    await waitFor(() => {
      expect(pressedOf(screen.getByRole('table', { name: GENERAL }), FAILED_CYCLE)).toEqual([
        'Telegram',
        'email',
      ]);
    });
  });

  it('turns the last channel off and the event reaches nobody', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(switchOf(await generalTable(), FAILED_CYCLE, 'Telegram'));

    await waitFor(() => {
      expect(fakeNotificationChannels.channelsOf('anna', FAILED_CYCLE)).toEqual([]);
    });
  });

  it('disables a channel not configured, with its reason and the way to configure it', async () => {
    fakePlatform.unlinkChat('anna');
    fakeNotificationChannels.choose('anna', FAILED_CYCLE, []);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const table = await generalTable();

    const telegram = switchOf(table, FAILED_CYCLE, 'Telegram');
    expect(telegram).toBeDisabled();
    expect(telegram).toHaveAccessibleDescription(/Telegram non collegato/);
    expect(switchOf(table, FAILED_CYCLE, 'email')).toBeEnabled();
    const toConfigure = screen.getByRole('status', { name: 'Canali da configurare' });
    expect(toConfigure).toHaveTextContent('Canali da configurare: Telegram non collegato.');
    expect(within(toConfigure).getByRole('link', { name: 'Configura' })).toHaveAttribute(
      'href',
      expect.stringContaining('tab=channels'),
    );
  });

  it('keeps a chosen channel not configured switchable off, warning beside the event', async () => {
    fakePlatform.unlinkChat('anna');
    fakePlatform.removeNotificationEmail('anna');
    fakeNotificationChannels.choose('anna', FAILED_CYCLE, ['Telegram', 'email']);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const table = await generalTable();

    expect(rowOf(table, FAILED_CYCLE)).toHaveTextContent(
      'Telegram non collegato, email non indicata',
    );
    expect(
      within(rowOf(table, FAILED_CYCLE)).getByRole('link', { name: 'Configura' }),
    ).toBeVisible();
    expect(rowOf(table, REDUCED)).not.toHaveTextContent('non collegato');
    await userEvent.click(switchOf(table, FAILED_CYCLE, 'Telegram'));

    await waitFor(() => {
      expect(fakeNotificationChannels.channelsOf('anna', FAILED_CYCLE)).toEqual(['email']);
    });
  });

  it('tells why a choice was not saved', async () => {
    server.use(
      http.put('*/notifications/channels', () =>
        HttpResponse.json(
          { title: 'Service Unavailable', status: 503, detail: 'servizio non disponibile' },
          { status: 503 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.click(switchOf(await generalTable(), FAILED_CYCLE, 'email'));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: servizio non disponibile',
    );
  });

  it('shows the exceptions of the chosen flow without the events of the account', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    fakeNotificationChannels.except('anna', alfa.id, FAILED_CYCLE, ['email']);
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await chooseFlowAlfa();
    const exceptions = await exceptionsTable();

    expect(pressedOf(exceptions, FAILED_CYCLE)).toEqual(['email']);
    expect(pressedOf(exceptions, OPENING)).toEqual([AS_GENERAL, 'Telegram']);
    expect(within(exceptions).queryByText(ALARM)).toBeNull();
  });

  it('sets an exception of the flow from the general choice and takes it away', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    await chooseFlowAlfa();

    await userEvent.click(switchOf(await exceptionsTable(), OPENING, 'email'));
    await waitFor(() => {
      expect(fakeNotificationChannels.exceptionsOf('anna', alfa.id).get(OPENING)).toEqual([
        'Telegram',
        'email',
      ]);
    });
    await waitFor(() => {
      expect(
        switchOf(screen.getByRole('table', { name: 'Eccezioni di alfa' }), OPENING, AS_GENERAL),
      ).toHaveAttribute('aria-pressed', 'false');
    });
    await userEvent.click(
      switchOf(screen.getByRole('table', { name: 'Eccezioni di alfa' }), OPENING, AS_GENERAL),
    );

    await waitFor(() => {
      expect(fakeNotificationChannels.exceptionsOf('anna', alfa.id).has(OPENING)).toBe(false);
    });
  });

  it('pressing «Come la scelta generale» on an event without exception changes nothing', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    await chooseFlowAlfa();

    await userEvent.click(switchOf(await exceptionsTable(), OPENING, AS_GENERAL));

    expect(fakeNotificationChannels.exceptionsOf('anna', alfa.id).size).toBe(0);
  });

  it('tells why an exception was not set', async () => {
    fakePlatform.giveFlowTo('anna', 'alfa');
    server.use(
      http.put('*/notifications/channels/flows/:flowId/:event', () =>
        HttpResponse.json(
          { title: 'Not Found', status: 404, detail: 'flusso non trovato' },
          { status: 404 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    await chooseFlowAlfa();

    await userEvent.click(switchOf(await exceptionsTable(), OPENING, 'email'));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: flusso non trovato',
    );
  });

  it('tells why the channels could not be read', async () => {
    server.use(
      http.get('*/notifications/channels', () =>
        HttpResponse.json(
          { title: 'Service Unavailable', status: 503, detail: 'servizio non disponibile' },
          { status: 503 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    expect(await screen.findByText(/servizio non disponibile/)).toBeInTheDocument();
  });
});
