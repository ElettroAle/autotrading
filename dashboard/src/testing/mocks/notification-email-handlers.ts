import { http, HttpResponse } from 'msw';

import { fakePlatform, type FakeMailServer } from './platform';
import { problem, withUser } from './responses';

/** The subject of the test email, the same the API sends (R3.5.2). */
export const TEST_EMAIL_SUBJECT = 'AutoTrading: prova delle notifiche';

export const MAIL_SERVER_MISSING = 'le email non partono: server di posta non configurato';

export const MAIL_LOGIN_REFUSED =
  "il server di posta ha rifiutato l'accesso: controlla utente e password";

// The same form the API checks: the dashboard leaves the judgement to the API.
const EMAIL_FORM = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const HIGHEST_PORT = 65_535;

const settingsOf = (account: string) => ({
  address: fakePlatform.notificationEmailOf(account) ?? null,
  warning: fakePlatform.mailServerOf(account) === undefined ? MAIL_SERVER_MISSING : null,
});

const addressOf = async (request: Request): Promise<string> => {
  const body = (await request.json()) as { address?: unknown };
  return typeof body.address === 'string' ? body.address.trim() : '';
};

// The answer of the API: never the password, only that one is saved (ADR server-di-posta-per-tenant).
const answerOf = ({ password, ...server }: FakeMailServer) => ({
  ...server,
  password_saved: password !== '',
});

type MailServerBody = {
  readonly host?: unknown;
  readonly port?: unknown;
  readonly security?: unknown;
  readonly username?: unknown;
  readonly sender?: unknown;
  readonly password?: unknown;
};

const textOf = (value: unknown): string => (typeof value === 'string' ? value.trim() : '');

// The same refusals the domain gives, the first that applies; undefined for a server the platform keeps.
const refusalOf = (body: MailServerBody, port: number) => {
  if (textOf(body.host) === '') {
    return problem(400, 'Bad Request', 'server di posta non valido', { host: body.host });
  }
  if (!Number.isInteger(port) || port < 1 || port > HIGHEST_PORT) {
    return problem(400, 'Bad Request', 'porta del server di posta non valida: da 1 a 65535', {
      port,
    });
  }
  if (textOf(body.username) === '') {
    return problem(400, 'Bad Request', 'utente del server di posta mancante', {
      username: body.username,
    });
  }
  return undefined;
};

const saveServer = async (account: string, request: Request) => {
  const body = (await request.json()) as MailServerBody;
  const security = body.security;
  if (security !== 'STARTTLS' && security !== 'TLS') {
    return problem(422, 'Unprocessable Entity', 'richiesta non valida');
  }
  const port = Number(body.port);
  const refusal = refusalOf(body, port);
  if (refusal !== undefined) {
    return refusal;
  }
  // A change without a password keeps the saved one; the first server needs one.
  const password = textOf(body.password) || (fakePlatform.mailServerOf(account)?.password ?? '');
  if (password === '') {
    return problem(400, 'Bad Request', 'password del server di posta mancante');
  }
  const username = textOf(body.username);
  fakePlatform.saveMailServer(account, {
    host: textOf(body.host),
    port,
    security,
    username,
    sender: textOf(body.sender) || username,
    password,
  });
  return new HttpResponse(null, { status: 204 });
};

const sendTest = (account: string) => {
  const server = fakePlatform.mailServerOf(account);
  if (server === undefined) {
    return problem(409, 'Conflict', 'server di posta non configurato');
  }
  const address = fakePlatform.notificationEmailOf(account);
  if (address === undefined) {
    return problem(409, 'Conflict', 'nessun indirizzo email per le notifiche');
  }
  if (fakePlatform.mailLoginRefused()) {
    return problem(400, 'Bad Request', MAIL_LOGIN_REFUSED);
  }
  fakePlatform.sendEmail({ to: address, subject: TEST_EMAIL_SUBJECT, host: server.host });
  return new HttpResponse(null, { status: 204 });
};

export const notificationEmailHandlers = [
  http.get('*/notifications/email', ({ request }) =>
    withUser(request, (user) => HttpResponse.json(settingsOf(user.account))),
  ),
  http.put('*/notifications/email', ({ request }) =>
    withUser(request, async (user) => {
      const address = await addressOf(request);
      if (!EMAIL_FORM.test(address)) {
        return problem(400, 'Bad Request', 'indirizzo email non valido');
      }
      fakePlatform.setNotificationEmail(user.account, address);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.delete('*/notifications/email', ({ request }) =>
    withUser(request, (user) => {
      fakePlatform.removeNotificationEmail(user.account);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.post('*/notifications/email/test', ({ request }) =>
    withUser(request, (user) => sendTest(user.account)),
  ),
  http.get('*/notifications/mail-server', ({ request }) =>
    withUser(request, (user) => {
      const server = fakePlatform.mailServerOf(user.account);
      return HttpResponse.json(server === undefined ? null : answerOf(server));
    }),
  ),
  http.put('*/notifications/mail-server', ({ request }) =>
    withUser(request, (user) => saveServer(user.account, request)),
  ),
  http.delete('*/notifications/mail-server', ({ request }) =>
    withUser(request, (user) => {
      fakePlatform.removeMailServer(user.account);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
];
