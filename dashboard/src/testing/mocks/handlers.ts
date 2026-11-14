import { http, HttpResponse } from 'msw';

import { summaryOf, type FakeCycle } from './cycles';
import { fakePlatform, type FakeFlow, type FakeUser } from './platform';

const BEARER = 'Bearer ';
const NO_LINKED_CHAT = 'nessuna chat collegata';

/** The text of the test notification of R1.8.1, the same from the chat and from the dashboard. */
export const TEST_NOTIFICATION = 'notifica di prova: le notifiche dei tuoi flussi arrivano qui';

const CYCLES_PER_PAGE = 50;

// Answers as the API does: Problem Details, 401 without a valid token, 403 without the Utente role (R0.1.1).
const problem = (status: number, title: string, detail: string) =>
  HttpResponse.json(
    { type: 'about:blank', title, status, detail },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

const userOf = (request: Request) => {
  const authorization = request.headers.get('Authorization') ?? '';
  return authorization.startsWith(BEARER)
    ? fakePlatform.userOfToken(authorization.slice(BEARER.length))
    : undefined;
};

const withUser = (
  request: Request,
  respond: (user: NonNullable<ReturnType<typeof userOf>>) => Response,
) => {
  const user = userOf(request);
  if (user === undefined) {
    return problem(401, 'Unauthorized', 'token assente o non valido');
  }
  if (!user.hasUserRole) {
    return problem(403, 'Forbidden', 'ruolo Utente assente');
  }
  return respond(user);
};

const flowResponse = (flow: FakeFlow) => ({
  id: flow.id,
  name: flow.name,
  account_id: 'account-1',
  status: flow.status,
  version: 1,
  assets: ['BTC'],
  cycle_minutes: 15,
  model: { name: 'openai/gpt-4o', parameters: {} },
  sources: [],
  instructions: '',
  risk_limits: {
    max_leverage: 3,
    max_margin_exposure_percent: null,
    max_value_exposure_percent: null,
  },
  allocated_capital: '100',
  bring_to_minimum: false,
});

const newestFirst = (cycles: FakeCycle[]): FakeCycle[] =>
  [...cycles].sort((one, other) => Date.parse(other.planned_at) - Date.parse(one.planned_at));

// A flow of another tenant does not exist for the user, as on the API (R0.1.3).
const withFlow = (
  user: FakeUser,
  flowId: string,
  respond: (cycles: FakeCycle[]) => Response,
): Response => {
  if (!user.flows.some((flow) => flow.id === flowId)) {
    return problem(404, 'Not Found', 'flusso non trovato');
  }
  return respond(fakePlatform.cyclesOf(flowId));
};

const cyclePage = (cycles: FakeCycle[], page: number) => {
  const start = (page - 1) * CYCLES_PER_PAGE;
  const sorted = newestFirst(cycles);
  return {
    page,
    has_next: sorted.length > start + CYCLES_PER_PAGE,
    cycles: sorted.slice(start, start + CYCLES_PER_PAGE).map(summaryOf),
  };
};

const cycleAt = (cycles: FakeCycle[], plannedAt: string): Response => {
  const cycle = cycles.find(
    (candidate) => Date.parse(candidate.planned_at) === Date.parse(plannedAt),
  );
  return cycle === undefined
    ? problem(404, 'Not Found', 'ciclo non trovato')
    : HttpResponse.json(cycle);
};

export const handlers = [
  http.get('*/me', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({ user_id: user.account, tenant_id: user.tenantId }),
    ),
  ),
  http.get('*/flows', ({ request }) =>
    withUser(request, (user) => HttpResponse.json(user.flows.map(flowResponse))),
  ),
  http.post('*/telegram/link-code', ({ request }) =>
    withUser(request, (user) => {
      const issued = fakePlatform.issueLinkCode(user.account, new Date());
      return HttpResponse.json(
        { code: issued.code, expires_at: issued.expiresAt, link: issued.link },
        { status: 201 },
      );
    }),
  ),
  http.get('*/telegram/chat', ({ request }) =>
    withUser(request, (user) => {
      const chat = fakePlatform.linkedChatOf(user.account);
      return HttpResponse.json({ linked: chat !== undefined, chat_id: chat?.id ?? null });
    }),
  ),
  http.delete('*/telegram/chat', ({ request }) =>
    withUser(request, (user) =>
      fakePlatform.unlinkChat(user.account)
        ? new HttpResponse(null, { status: 204 })
        : problem(404, 'Not Found', NO_LINKED_CHAT),
    ),
  ),
  http.post('*/telegram/test-notification', ({ request }) =>
    withUser(request, (user) => {
      const chat = fakePlatform.linkedChatOf(user.account);
      if (chat === undefined) {
        return problem(409, 'Conflict', NO_LINKED_CHAT);
      }
      chat.received.push(TEST_NOTIFICATION);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.get('*/flows/:flowId/cycles', ({ request, params }) =>
    withUser(request, (user) =>
      withFlow(user, String(params.flowId), (cycles) =>
        HttpResponse.json(
          cyclePage(cycles, Number(new URL(request.url).searchParams.get('page') ?? '1')),
        ),
      ),
    ),
  ),
  http.get('*/flows/:flowId/cycles/:plannedAt', ({ request, params }) =>
    withUser(request, (user) =>
      withFlow(user, String(params.flowId), (cycles) => cycleAt(cycles, String(params.plannedAt))),
    ),
  ),
];
