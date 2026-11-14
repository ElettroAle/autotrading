import { http, HttpResponse } from 'msw';

import { fakePlatform, type FakeFlow } from './platform';

const BEARER = 'Bearer ';

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

export const handlers = [
  http.get('*/me', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({ user_id: user.account, tenant_id: user.tenantId }),
    ),
  ),
  http.get('*/flows', ({ request }) =>
    withUser(request, (user) => HttpResponse.json(user.flows.map(flowResponse))),
  ),
];
