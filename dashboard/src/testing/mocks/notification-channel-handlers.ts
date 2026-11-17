import { http, HttpResponse } from 'msw';

import {
  FAKE_CHANNELS,
  FAKE_EVENT_TYPES,
  fakeNotificationChannels,
  type FakeChannel,
} from './notification-channels';
import { fakePlatform } from './platform';
import { problem, withUser } from './responses';

const ARCHIVED = 'archiviato';
const TELEGRAM_NOT_LINKED = 'Telegram non collegato';
const EMAIL_NOT_INDICATED = 'email non indicata';

const isChannel = (value: unknown): value is FakeChannel =>
  FAKE_CHANNELS.some((channel) => channel === value);

const typeOf = (event: unknown) => FAKE_EVENT_TYPES.find((type) => type.event === event);

// The same warnings the API computes: a chosen channel with nothing linked sends nothing (R3.5.3).
const warningsOf = (account: string, channel: FakeChannel): string[] => [
  ...(['Telegram', 'entrambi'].includes(channel) && fakePlatform.linkedChatOf(account) === undefined
    ? [TELEGRAM_NOT_LINKED]
    : []),
  ...(['email', 'entrambi'].includes(channel) &&
  fakePlatform.notificationEmailOf(account) === undefined
    ? [EMAIL_NOT_INDICATED]
    : []),
];

const eventChannel = (account: string, event: string, channel: FakeChannel) => ({
  event,
  channel,
  of_flow: typeOf(event)?.ofFlow ?? true,
  warnings: warningsOf(account, channel),
});

const flowsOf = (account: string) =>
  fakePlatform.flowsOf(account).filter((flow) => flow.status !== ARCHIVED);

const channelsOf = (account: string) => ({
  events: FAKE_EVENT_TYPES.map(({ event }) =>
    eventChannel(account, event, fakeNotificationChannels.channelOf(account, event)),
  ),
  flows: flowsOf(account)
    .sort((first, second) => first.name.localeCompare(second.name))
    .map((flow) => ({
      flow_id: flow.id,
      name: flow.name,
      exceptions: [...fakeNotificationChannels.exceptionsOf(account, flow.id)].map(
        ([event, channel]) => eventChannel(account, event, channel),
      ),
    })),
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
      const { event, channel } = await bodyOf(request);
      if (typeOf(event) === undefined || !isChannel(channel)) {
        return invalid();
      }
      fakeNotificationChannels.choose(user.account, String(event), channel);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.put('*/notifications/channels/flows/:flowId/:event', ({ request, params }) =>
    withUser(request, async (user) => {
      const { channel } = await bodyOf(request);
      const type = typeOf(params.event);
      if (type === undefined || !isChannel(channel)) {
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
      fakeNotificationChannels.except(user.account, String(params.flowId), type.event, channel);
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
