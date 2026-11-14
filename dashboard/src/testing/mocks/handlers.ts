import { http, HttpResponse } from 'msw';

import { summaryOf, type FakeCycle } from './cycles';
import { InvalidPeriod, periodAdmits, statisticsOf } from './flow-statistics';
import {
  FakeRefusal,
  fakePlatform,
  type FakeConfiguration,
  type FakeAccount,
  type FakeEquityPoint,
  type FakeFlow,
  type FakeUser,
} from './platform';
import type { FakeClosedPosition } from './positions';

const BEARER = 'Bearer ';
const NO_LINKED_CHAT = 'nessuna chat collegata';

/** The text of the test notification of R1.8.1, the same from the chat and from the dashboard. */
export const TEST_NOTIFICATION = 'notifica di prova: le notifiche dei tuoi flussi arrivano qui';

const CYCLES_PER_PAGE = 50;
const CLOSED_POSITIONS_PER_PAGE = 50;
const CURRENCY = 'USDC';

// Answers as the API does: Problem Details, 401 without a valid token, 403 without the Utente role (R0.1.1).
const problem = (status: number, title: string, detail: string) =>
  HttpResponse.json(
    { type: 'about:blank', title, status, detail },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

const notFound = (detail: string) => problem(404, 'Not Found', detail);

const userOf = (request: Request) => {
  const authorization = request.headers.get('Authorization') ?? '';
  return authorization.startsWith(BEARER)
    ? fakePlatform.userOfToken(authorization.slice(BEARER.length))
    : undefined;
};

const withUser = async (
  request: Request,
  respond: (user: FakeUser) => Response | Promise<Response>,
): Promise<Response> => {
  const user = userOf(request);
  if (user === undefined) {
    return problem(401, 'Unauthorized', 'token assente o non valido');
  }
  if (!user.hasUserRole) {
    return problem(403, 'Forbidden', 'ruolo Utente assente');
  }
  try {
    return await respond(user);
  } catch (error) {
    if (error instanceof FakeRefusal) {
      return problem(error.status, 'Refused', error.message);
    }
    throw error;
  }
};

// A flow of another tenant is not found, as one that does not exist (R0.1.3).
const withFlow = (request: Request, flowId: unknown, respond: (flow: FakeFlow) => Response) =>
  withUser(request, (user) => {
    const flow = user.flows.find((candidate) => candidate.id === flowId);
    return flow === undefined ? notFound('flusso non trovato') : respond(flow);
  });

const withConfiguration = (
  flow: FakeFlow,
  number: unknown,
  respond: (configuration: FakeConfiguration) => Response,
) => {
  const version = flow.versions.find((candidate) => String(candidate.number) === number);
  return version === undefined
    ? notFound(`versione di configurazione non trovata: ${String(number)}`)
    : respond(version.configuration);
};

const configurationResponse = (configuration: FakeConfiguration) => ({
  assets: configuration.assets,
  cycle_minutes: configuration.cycleMinutes,
  model: { name: configuration.model, parameters: {} },
  sources: [],
  instructions: configuration.instructions,
  risk_limits: {
    max_leverage: configuration.maxLeverage,
    max_margin_exposure_percent: null,
    max_value_exposure_percent: null,
  },
  allocated_capital: configuration.allocatedCapital,
  bring_to_minimum: false,
});

const accountResponse = (user: FakeUser, account: FakeAccount) => ({
  id: account.id,
  name: account.name,
  exchange: 'Hyperliquid',
  has_credentials: true,
  network: 'test',
  allocated_capital: String(fakePlatform.allocatedCapitalOf(user, account)),
  currency: CURRENCY,
});

const amountOf = (amount: string) => ({ amount, currency: CURRENCY });

const accountStateResponse = (account: FakeAccount) => ({
  balance: amountOf(String(account.balance)),
  available_margin: amountOf(String(account.balance)),
  positions: [],
  read_at: '2026-11-14T09:00:00+00:00',
});

const freeCapitalResponse = (user: FakeUser, account: FakeAccount) =>
  amountOf(String(fakePlatform.freeCapitalOfAccount(user, account)));

// An account of another tenant does not exist for the user; what comes from the exchange fails when it does not answer.
const withAccountOnExchange = (
  user: FakeUser,
  accountId: string,
  respond: (account: FakeAccount) => Response,
): Response => {
  const account = user.accounts.find((candidate) => candidate.id === accountId);
  if (account === undefined) {
    return problem(404, 'Not Found', 'non trovato');
  }
  if (!fakePlatform.exchangeReachable()) {
    return problem(503, 'Service Unavailable', 'exchange non raggiungibile, riprovare');
  }
  return respond(account);
};

const newestFirst = (cycles: FakeCycle[]): FakeCycle[] =>
  [...cycles].sort((one, other) => Date.parse(other.planned_at) - Date.parse(one.planned_at));

const pageOf = (request: Request): number =>
  Number(new URL(request.url).searchParams.get('page') ?? '1');

const flowState = (flowId: string) => ({
  flow_id: flowId,
  currency: CURRENCY,
  allocated_capital: '500',
  available_liquidity: '300',
  margin: '200',
  unrealized_pnl: '12',
  realized_pnl: '0',
  fees: '0',
  total_value: '512',
  return_percent: '2.4',
  positions: fakePlatform.openPositionsOf(flowId),
});

const closedPositionPage = (positions: FakeClosedPosition[], page: number) => {
  const start = (page - 1) * CLOSED_POSITIONS_PER_PAGE;
  const sorted = [...positions].sort(
    (one, other) => Date.parse(other.closed_at) - Date.parse(one.closed_at),
  );
  return {
    page,
    has_next: sorted.length > start + CLOSED_POSITIONS_PER_PAGE,
    positions: sorted.slice(start, start + CLOSED_POSITIONS_PER_PAGE),
  };
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

const equityResponse = (flow: FakeFlow, admits: (instant: Date) => boolean) => ({
  // A draft has no capital, and no cycle yet (ADR 0124).
  initial_capital: flow.allocatedCapital === null ? null : String(flow.allocatedCapital),
  points: flow.equity
    .filter((point: FakeEquityPoint) => admits(point.plannedAt))
    .toSorted((first, second) => first.plannedAt.getTime() - second.plannedAt.getTime())
    .map((point) => ({ planned_at: point.plannedAt.toISOString(), equity: String(point.equity) })),
});

// The parts the API compares, with the same names and texts (R1.1.3): the fake never compares in another way.
const PARTS: [string, (configuration: FakeConfiguration) => string][] = [
  ['asset', (configuration) => configuration.assets.join(', ')],
  ['intervallo di ciclo', (configuration) => `${configuration.cycleMinutes} minuti`],
  ['modello', (configuration) => configuration.model],
  ['istruzioni', (configuration) => configuration.instructions],
  ['leva massima', (configuration) => String(configuration.maxLeverage)],
  ['capitale allocato', (configuration) => configuration.allocatedCapital],
];

const differences = (before: FakeConfiguration, after: FakeConfiguration) =>
  PARTS.map(([part, text]) => ({ part, before: text(before), after: text(after) })).filter(
    (difference) => difference.before !== difference.after,
  );

const flowResponse = (flow: FakeFlow) => ({
  id: flow.id,
  name: flow.name,
  account_id: flow.accountId,
  status: flow.status,
  version: flow.version,
  assets: flow.assets,
  cycle_minutes: flow.cycleMinutes,
  model: { name: flow.model, parameters: {} },
  sources: flow.sources.map((source) => ({ ...source, parameters: {} })),
  instructions: '',
  risk_limits: {
    max_leverage: 3,
    max_margin_exposure_percent: '10',
    max_value_exposure_percent: null,
  },
  allocated_capital: flow.allocatedCapital === null ? null : String(flow.allocatedCapital),
  bring_to_minimum: false,
});

type AssignmentRequest = { account_id: string; allocated_capital: string; assets?: string[] };

export const handlers = [
  http.get('*/me', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({ user_id: user.account, tenant_id: user.tenantId }),
    ),
  ),
  http.get('*/accounts', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json(user.accounts.map((account) => accountResponse(user, account))),
    ),
  ),
  http.get('*/accounts/:accountId/state', ({ request, params }) =>
    withUser(request, (user) =>
      withAccountOnExchange(user, String(params.accountId), (account) =>
        HttpResponse.json(accountStateResponse(account)),
      ),
    ),
  ),
  http.get('*/accounts/:accountId/free-capital', ({ request, params }) =>
    withUser(request, (user) =>
      withAccountOnExchange(user, String(params.accountId), (account) =>
        HttpResponse.json(freeCapitalResponse(user, account)),
      ),
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
    withFlow(request, params.flowId, (flow) =>
      HttpResponse.json(cyclePage(fakePlatform.cyclesOf(flow.id), pageOf(request))),
    ),
  ),
  http.get('*/flows/:flowId/versions', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      HttpResponse.json(
        flow.versions
          .map((version) => ({ version: version.number, created_at: version.createdAt }))
          .reverse(),
      ),
    ),
  ),
  http.get('*/flows/:flowId/versions/:version', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      withConfiguration(flow, params.version, (configuration) =>
        HttpResponse.json({
          version: Number(params.version),
          ...configurationResponse(configuration),
        }),
      ),
    ),
  ),
  http.get('*/flows/:flowId/versions/:first/differences/:second', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      withConfiguration(flow, params.first, (first) =>
        withConfiguration(flow, params.second, (second) =>
          HttpResponse.json(differences(first, second)),
        ),
      ),
    ),
  ),
  http.get('*/flows/:flowId/cycles/:plannedAt', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      cycleAt(fakePlatform.cyclesOf(flow.id), String(params.plannedAt)),
    ),
  ),
  http.get('*/flows/:flowId/equity', ({ request, params }) =>
    withUser(request, (user) => {
      const flow = user.flows.find((candidate) => candidate.id === params.flowId);
      if (flow === undefined) {
        return problem(404, 'Not Found', 'flusso non trovato');
      }
      try {
        return HttpResponse.json(
          equityResponse(flow, periodAdmits(new URL(request.url).searchParams)),
        );
      } catch (error) {
        if (error instanceof InvalidPeriod) {
          return problem(400, 'Bad Request', error.message);
        }
        throw error;
      }
    }),
  ),
  http.get('*/flows/:flowId/statistics', ({ request, params }) =>
    withUser(request, (user) => {
      const flow = user.flows.find((candidate) => candidate.id === params.flowId);
      if (flow === undefined) {
        return problem(404, 'Not Found', 'flusso non trovato');
      }
      try {
        return HttpResponse.json(statisticsOf(flow.history, new URL(request.url).searchParams));
      } catch (error) {
        if (error instanceof InvalidPeriod) {
          return problem(400, 'Bad Request', error.message);
        }
        throw error;
      }
    }),
  ),
  http.post('*/flows/:flowId/duplicate', ({ request, params }) =>
    withUser(request, (user) =>
      HttpResponse.json(flowResponse(fakePlatform.duplicate(user, String(params.flowId))), {
        status: 201,
      }),
    ),
  ),
  http.put('*/flows/:flowId/assignment', ({ request, params }) =>
    withUser(request, async (user) => {
      const body = (await request.json()) as AssignmentRequest;
      const assignment = {
        accountId: body.account_id,
        allocatedCapital: Number(body.allocated_capital),
        assets: body.assets ?? [],
      };
      return HttpResponse.json(
        flowResponse(fakePlatform.assign(user, String(params.flowId), assignment)),
      );
    }),
  ),
  http.post('*/flows/:flowId/start', ({ request, params }) =>
    withUser(request, (user) =>
      HttpResponse.json(flowResponse(fakePlatform.start(user, String(params.flowId)))),
    ),
  ),
  http.get('*/flows/:flowId/state', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) => HttpResponse.json(flowState(flow.id))),
  ),
  http.get('*/flows/:flowId/closed-positions', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      HttpResponse.json(
        closedPositionPage(fakePlatform.closedPositionsOf(flow.id), pageOf(request)),
      ),
    ),
  ),
];
