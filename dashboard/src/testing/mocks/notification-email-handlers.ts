import { http, HttpResponse } from 'msw';

import { fakePlatform } from './platform';
import { problem, withUser } from './responses';

/** The subject of the test email, the same the API sends (R3.5.2). */
export const TEST_EMAIL_SUBJECT = 'AutoTrading: prova delle notifiche';

export const MAIL_SERVICE_MISSING = 'le email non partono: servizio di posta non configurato';

// The same form the API checks: the dashboard leaves the judgement to the API.
const EMAIL_FORM = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const settingsOf = (account: string) => ({
  address: fakePlatform.notificationEmailOf(account) ?? null,
  warning: fakePlatform.mailServiceConfigured() ? null : MAIL_SERVICE_MISSING,
});

const addressOf = async (request: Request): Promise<string> => {
  const body = (await request.json()) as { address?: unknown };
  return typeof body.address === 'string' ? body.address.trim() : '';
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
    withUser(request, (user) => {
      if (!fakePlatform.mailServiceConfigured()) {
        return problem(409, 'Conflict', 'servizio di posta non configurato');
      }
      const address = fakePlatform.notificationEmailOf(user.account);
      if (address === undefined) {
        return problem(409, 'Conflict', 'nessun indirizzo email per le notifiche');
      }
      fakePlatform.sendEmail({ to: address, subject: TEST_EMAIL_SUBJECT });
      return new HttpResponse(null, { status: 202 });
    }),
  ),
];
