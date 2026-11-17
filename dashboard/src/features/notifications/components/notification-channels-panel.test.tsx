import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakeNotificationChannels } from '@/testing/mocks/notification-channels';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NOTIFICATIONS = '/notifications';
const GENERAL = 'Canali per tipo di evento';
const FAILED_CYCLE = 'ciclo fallito';
const OPENING = 'apertura di una posizione';
const ALARM = 'allarme di riconciliazione';

const generalTable = async () => screen.findByRole('table', { name: GENERAL });

const rowOf = (table: HTMLElement, event: string): HTMLElement => {
  const row = within(table)
    .getAllByRole('row')
    .find((candidate) => within(candidate).queryByText(event) !== null);
  if (row === undefined) {
    throw new Error(`no row for ${event}`);
  }
  return row;
};

const channelOf = (table: HTMLElement, event: string) =>
  within(table).getByRole('combobox', { name: `Canale di ${event}` });

// ADR-scelta-dei-canali-nella-dashboard: the channels of the API in the shared table, the exceptions of a flow and the
// warnings of a channel not linked.
describe('NotificationChannelsPanel', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.linkChat('anna', 'chat-anna');
    fakePlatform.setNotificationEmail('anna', 'anna@example.com');
  });

  it('shows every type of event with the channel the API gives it', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const table = await generalTable();

    expect(channelOf(table, OPENING)).toHaveValue('Telegram');
    expect(channelOf(table, 'decisione ridotta dal rischio')).toHaveValue('nessuno');
    expect(channelOf(table, ALARM)).toHaveValue('Telegram');
  });

  it('saves the channel the user chooses for a type of event', async () => {
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.selectOptions(channelOf(await generalTable(), FAILED_CYCLE), 'email');

    await waitFor(() => {
      expect(fakeNotificationChannels.channelOf('anna', FAILED_CYCLE)).toBe('email');
    });
    await waitFor(() => {
      expect(channelOf(screen.getByRole('table', { name: GENERAL }), FAILED_CYCLE)).toHaveValue(
        'email',
      );
    });
  });

  it('warns beside the event when the chosen channel is not linked', async () => {
    fakePlatform.unlinkChat('anna');
    fakePlatform.removeNotificationEmail('anna');
    fakeNotificationChannels.choose('anna', FAILED_CYCLE, 'entrambi');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    const table = await generalTable();

    expect(rowOf(table, FAILED_CYCLE)).toHaveTextContent(
      'Telegram non collegato, email non indicata',
    );
    expect(rowOf(table, 'decisione ridotta dal rischio')).not.toHaveTextContent('non collegato');
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

    await userEvent.selectOptions(channelOf(await generalTable(), FAILED_CYCLE), 'email');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: servizio non disponibile',
    );
  });

  it('shows the exceptions of the chosen flow without the events of the account', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    fakeNotificationChannels.except('anna', alfa.id, FAILED_CYCLE, 'nessuno');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });

    await userEvent.selectOptions(await screen.findByLabelText('Flusso'), 'alfa');
    const exceptions = await screen.findByRole('table', { name: 'Eccezioni di alfa' });

    expect(channelOf(exceptions, FAILED_CYCLE)).toHaveValue('nessuno');
    expect(channelOf(exceptions, OPENING)).toHaveValue('');
    expect(within(exceptions).queryByText(ALARM)).toBeNull();
  });

  it('sets an exception of the flow and takes it away', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    await renderApp({ account: 'anna', url: NOTIFICATIONS });
    await userEvent.selectOptions(await screen.findByLabelText('Flusso'), 'alfa');
    const exceptions = await screen.findByRole('table', { name: 'Eccezioni di alfa' });

    await userEvent.selectOptions(channelOf(exceptions, OPENING), 'Telegram');
    await waitFor(() => {
      expect(fakeNotificationChannels.exceptionsOf('anna', alfa.id).get(OPENING)).toBe('Telegram');
    });
    await userEvent.selectOptions(
      channelOf(screen.getByRole('table', { name: 'Eccezioni di alfa' }), OPENING),
      'come la scelta generale',
    );

    await waitFor(() => {
      expect(fakeNotificationChannels.exceptionsOf('anna', alfa.id).has(OPENING)).toBe(false);
    });
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
    await userEvent.selectOptions(await screen.findByLabelText('Flusso'), 'alfa');

    await userEvent.selectOptions(
      channelOf(await screen.findByRole('table', { name: 'Eccezioni di alfa' }), OPENING),
      'email',
    );

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
