import { http, HttpResponse } from 'msw';

import type { FakeAccount, FakeUser } from './platform';
import { fakeReconciliation, THRESHOLD_OUT_OF_RANGE } from './reconciliation';
import { problem, textFieldsOf, withUser } from './responses';

// An account of another tenant is not found, as one that does not exist (R0.1.3).
const withAccount = (
  request: Request,
  accountId: unknown,
  respond: (account: FakeAccount, user: FakeUser) => Response | Promise<Response>,
) =>
  withUser(request, (user) => {
    const account = user.accounts.find((candidate) => candidate.id === accountId);
    return account === undefined
      ? problem(404, 'Not Found', 'non trovato')
      : respond(account, user);
  });

/** The reconciliation of the balance of the accounts, as the API exposes it (R3.3.1). */
export const reconciliationHandlers = [
  http.get('*/accounts/:accountId/reconciliation', ({ request, params }) =>
    withAccount(request, params.accountId, (account) =>
      HttpResponse.json(fakeReconciliation.statusOf(account.id)),
    ),
  ),
  http.get('*/accounts/:accountId/reconciliation/alarms', ({ request, params }) =>
    withAccount(request, params.accountId, (account) =>
      HttpResponse.json(fakeReconciliation.alarmsOf(account.id)),
    ),
  ),
  http.post('*/accounts/:accountId/reconciliation/confirmation', ({ request, params }) =>
    withAccount(request, params.accountId, (account) =>
      fakeReconciliation.confirm(account.id, new Date())
        ? new HttpResponse(null, { status: 204 })
        : problem(
            409,
            'Conflict',
            `il conto ${account.name} non ha un allarme di riconciliazione aperto`,
          ),
    ),
  ),
  http.put('*/accounts/:accountId/deviation-threshold', ({ request, params }) =>
    withAccount(request, params.accountId, async (account) => {
      const { percent = '' } = await textFieldsOf(request);
      if (!fakeReconciliation.setThreshold(account.id, percent)) {
        return problem(422, 'Unprocessable Content', THRESHOLD_OUT_OF_RANGE, { percent });
      }
      return HttpResponse.json({ percent: fakeReconciliation.thresholdOf(account.id) });
    }),
  ),
];
