import { http, HttpResponse } from 'msw';

import { fakeInbox } from './notification-inbox';
import { problem, withUser } from './responses';

const NOT_FOUND = 'notifica non trovata';

/** The bell of the tenant, as the API exposes it (R6.2.1, ADR notifiche-nell-app-salvate-per-tenant). */
export const notificationInboxHandlers = [
  http.get('*/notifications/inbox', ({ request }) =>
    withUser(request, (user) => {
      const cursor = new URL(request.url).searchParams.get('cursor');
      return HttpResponse.json(fakeInbox.pageOf(user.tenantId, cursor));
    }),
  ),
  http.get('*/notifications/inbox/summary', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({ unread_count: fakeInbox.unreadCount(user.tenantId) }),
    ),
  ),
  http.post('*/notifications/inbox/read', ({ request }) =>
    withUser(request, (user) => {
      fakeInbox.markAllRead(user.tenantId, new Date());
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.post('*/notifications/inbox/:notificationId/read', ({ request, params }) =>
    withUser(request, (user) =>
      fakeInbox.markRead(user.tenantId, String(params.notificationId), new Date())
        ? new HttpResponse(null, { status: 204 })
        : problem(404, 'Not Found', NOT_FOUND),
    ),
  ),
];
