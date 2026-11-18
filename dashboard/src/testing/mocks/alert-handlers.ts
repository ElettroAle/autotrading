import { http, HttpResponse } from 'msw';

import { fakeAlerts, NOT_RESOLVABLE_BY_HAND, type FakeAlertAccount } from './alerts';
import type { FakeUser } from './platform';
import { problem, withUser } from './responses';

const NOT_FOUND = 'avviso non trovato';

const accountsOf = (user: FakeUser): FakeAlertAccount[] =>
  user.accounts.map(({ id, name, currency }) => ({ id, name, currency }));

/** The alerts of the tenant, as the API exposes them (R6.2.3, ADR api-degli-avvisi-e-link-nelle-notifiche). */
export const alertHandlers = [
  http.get('*/alerts', ({ request }) =>
    withUser(request, (user) => {
      const search = new URL(request.url).searchParams;
      const query = {
        state: search.get('state'),
        severity: search.get('severity'),
        resourceKind: search.get('resource_kind'),
        resourceId: search.get('resource_id'),
        since: search.get('since'),
        until: search.get('until'),
        cursor: search.get('cursor'),
      };
      return HttpResponse.json(fakeAlerts.pageOf(user.tenantId, accountsOf(user), query));
    }),
  ),
  // Before the detail, whose parameter would take «summary» for an id.
  http.get('*/alerts/summary', ({ request }) =>
    withUser(request, (user) => {
      const open = fakeAlerts
        .alertsOf(user.tenantId, accountsOf(user))
        .filter((alert) => alert.resolved_at === null);
      return HttpResponse.json({ open_count: open.length });
    }),
  ),
  http.get('*/alerts/:alertId', ({ request, params }) =>
    withUser(request, (user) => {
      const detail = fakeAlerts.detailOf(user.tenantId, accountsOf(user), String(params.alertId));
      return detail === undefined
        ? problem(404, 'Not Found', NOT_FOUND)
        : HttpResponse.json(detail);
    }),
  ),
  http.post('*/alerts/:alertId/resolution', ({ request, params }) =>
    withUser(request, (user) => {
      const alertId = String(params.alertId);
      const detail = fakeAlerts.detailOf(user.tenantId, accountsOf(user), alertId);
      if (detail === undefined) {
        return problem(404, 'Not Found', NOT_FOUND);
      }
      return fakeAlerts.resolveByHand(user.tenantId, alertId, new Date())
        ? new HttpResponse(null, { status: 204 })
        : problem(409, 'Conflict', NOT_RESOLVABLE_BY_HAND, { kind: detail.kind });
    }),
  ),
];
