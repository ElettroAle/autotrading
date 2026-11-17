import { http, HttpResponse } from 'msw';

import {
  FAKE_CHANNELS,
  FAKE_EVENT_TYPES,
  fakeNotificationChannels,
  type FakeChannel,
  type FakeChoice,
} from './notification-channels';
import { fakePlatform } from './platform';
import { problem, withUser } from './responses';

const ARCHIVED = 'archiviato';
const TELEGRAM_NOT_LINKED = 'Telegram non collegato';
const EMAIL_NOT_INDICATED = 'email non indicata';
const MAIL_SERVER_MISSING = 'server di posta non configurato';

const isChannel = (value: unknown): value is FakeChannel =>
  FAKE_CHANNELS.some((channel) => channel === value);

const isChoice = (value: unknown): value is FakeChannel[] =>
  Array.isArray(value) && value.every(isChannel);

const typeOf = (event: unknown) => FAKE_EVENT_TYPES.find((type) => type.event === event);

// The same warnings the API computes: a chosen channel with nothing linked sends nothing (R3.5.3), and no email
// leaves without the mail server of the user (R3.5.5).
const warningsOf = (account: string, channels: FakeChoice): string[] => {
  const reachesChat = channels.includes('Telegram');
  const reachesEmail = channels.includes('email');
  return [
    ...(reachesChat && fakePlatform.linkedChatOf(account) === undefined
      ? [TELEGRAM_NOT_LINKED]
      : []),
    ...(reachesEmail && fakePlatform.notificationEmailOf(account) === undefined
      ? [EMAIL_NOT_INDICATED]
      : []),
    ...(reachesEmail && fakePlatform.mailServerOf(account) === undefined
      ? [MAIL_SERVER_MISSING]
      : []),
  ];
};

const eventChannel = (account: string, event: string, channels: FakeChoice) => ({
  event,
  channels,
  of_flow: typeOf(event)?.ofFlow ?? true,
  warnings: warningsOf(account, channels),
});

// Every channel of the platform with what the user misses to reach it (ADR canali-delle-notifiche-come-insieme).
const channelState = (account: string, channel: FakeChannel) => {
  const warnings = warningsOf(account, [channel]);
  return { channel, configured: warnings.length === 0, warnings };
};

const flowsOf = (account: string) =>
  fakePlatform.flowsOf(account).filter((flow) => flow.status !== ARCHIVED);

const channelsOf = (account: string) => ({
  events: FAKE_EVENT_TYPES.map(({ event }) =>
    eventChannel(account, event, fakeNotificationChannels.channelsOf(account, event)),
  ),
  flows: flowsOf(account)
    .sort((first, second) => first.name.localeCompare(second.name))
    .map((flow) => ({
      flow_id: flow.id,
      name: flow.name,
      exceptions: [...fakeNotificationChannels.exceptionsOf(account, flow.id)].map(
        ([event, channels]) => eventChannel(account, event, channels),
      ),
    })),
  channels: FAKE_CHANNELS.map((channel) => channelState(account, channel)),
  warnings: warningsOf(account, FAKE_CHANNELS),
});

const invalid = () =>
  HttpResponse.json(
    { title: 'Unprocessable Entity', status: 422, detail: 'richiesta non valida' },
    { status: 422 },
  );

const bodyOf = async (request: Request): Promise<Record<string, unknown>> =>
  (await request.json()) as Record<string, unknown>;

export const notificationChannelHandlers = [
  http.get('*/notifications/channels', ({ request }) =>
    withUser(request, (user) => HttpResponse.json(channelsOf(user.account))),
  ),
  http.put('*/notifications/channels', ({ request }) =>
    withUser(request, async (user) => {
      const { event, channels } = await bodyOf(request);
      if (typeOf(event) === undefined || !isChoice(channels)) {
        return invalid();
      }
      fakeNotificationChannels.choose(user.account, String(event), channels);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.put('*/notifications/channels/flows/:flowId/:event', ({ request, params }) =>
    withUser(request, async (user) => {
      const { channels } = await bodyOf(request);
      const type = typeOf(params.event);
      if (type === undefined || !isChoice(channels)) {
        return invalid();
      }
      if (!flowsOf(user.account).some((flow) => flow.id === params.flowId)) {
        return problem(404, 'Not Found', 'flusso non trovato');
      }
      if (!type.ofFlow) {
        return problem(
          400,
          'Bad Request',
          `${type.event} è un evento del conto: segue la scelta generale`,
          { event: type.event },
        );
      }
      fakeNotificationChannels.except(user.account, String(params.flowId), type.event, channels);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.delete('*/notifications/channels/flows/:flowId/:event', ({ request, params }) =>
    withUser(request, (user) => {
      fakeNotificationChannels.removeException(
        user.account,
        String(params.flowId),
        String(params.event),
      );
      return new HttpResponse(null, { status: 204 });
    }),
  ),
];
