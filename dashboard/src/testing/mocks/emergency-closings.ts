import { http, HttpResponse } from 'msw';

import { apiInstant } from './cycles';
import { fakePlatform, type FakeEmergencyScope, type FakeUser } from './platform';
import { withUser } from './responses';

const NOTHING_TO_CLOSE = 'nessuna posizione da chiudere';

type ScopeRequest = { flow_id?: string | null; account_id?: string | null };

const scopeOf = ({ flow_id, account_id }: ScopeRequest): FakeEmergencyScope => ({
  ...(flow_id ? { flowId: flow_id } : {}),
  ...(account_id ? { accountId: account_id } : {}),
});

const kindOf = (scope: FakeEmergencyScope): string => {
  if (scope.flowId !== undefined) {
    return 'flow';
  }
  return scope.accountId === undefined ? 'all' : 'account';
};

// The positions of a flow that the API would close now: those the fake exchange shows for it.
const previewOf = (user: FakeUser, scope: FakeEmergencyScope) => {
  const flows = fakePlatform.emergencyFlowsOf(user, scope);
  const positions = flows.reduce(
    (total, flow) => total + fakePlatform.openPositionsOf(flow.id).length,
    0,
  );
  return { flows: flows.length, positions };
};

/** The emergency closing and its preview, as the API answers them (R3.2.3). */
export const emergencyClosingHandlers = [
  http.get('*/flows/emergency-closings/preview', ({ request }) =>
    withUser(request, (user) => {
      const search = new URL(request.url).searchParams;
      const scope = scopeOf({
        flow_id: search.get('flow_id'),
        account_id: search.get('account_id'),
      });
      return HttpResponse.json(previewOf(user, scope));
    }),
  ),
  http.post('*/flows/emergency-closings', async ({ request }) => {
    const scope = scopeOf((await request.json().catch(() => ({}))) as ScopeRequest);
    return withUser(request, (user) => {
      const outcomes = fakePlatform.closeInEmergency(user, scope);
      return HttpResponse.json({
        closed_at: apiInstant(new Date()),
        scope: {
          kind: kindOf(scope),
          flow_id: scope.flowId ?? null,
          account_id: scope.accountId ?? null,
        },
        flows: outcomes.map(({ flow, closed }) => ({
          flow_id: flow.id,
          flow_name: flow.name,
          closed,
          left_open: [],
          failure: null,
          remark: closed.length === 0 ? NOTHING_TO_CLOSE : null,
        })),
      });
    });
  }),
];
