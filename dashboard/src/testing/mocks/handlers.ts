import { http, HttpResponse } from 'msw';

import { accountHandlers } from './account-handlers';
import { FAKE_MODELS, FAKE_SOURCES } from './catalogs';
import { apiInstant, summaryOf, type FakeCycle } from './cycles';
import {
  changeAllocatedCapital,
  createFlow,
  InvalidRequest,
  modifyFlow,
  Refusal,
} from './flow-configuration';
import { InvalidPeriod, periodAdmits, statisticsOf } from './flow-statistics';
import { historyPage, InvalidSearch, type FakeHistoryRow, type FakeRecords } from './history';
import {
  configurationOf,
  FAKE_FLOW_COMMANDS,
  fakePlatform,
  type FakeFlowCommand,
  type FakeConfiguration,
  type FakeEquityPoint,
  type FakeFlow,
  type FakeStrategyDocument,
  type FakeUser,
} from './platform';
import type { FakeClosedPosition } from './positions';
import { providerKeyHandlers } from './provider-key-handlers';
import { problem, withUser } from './responses';

const NO_LINKED_CHAT = 'nessuna chat collegata';

/** The text of the test notification of R1.8.1, the same from the chat and from the dashboard. */
export const TEST_NOTIFICATION = 'notifica di prova: le notifiche dei tuoi flussi arrivano qui';

const CYCLES_PER_PAGE = 50;
const CLOSED_POSITIONS_PER_PAGE = 50;
const CURRENCY = 'USDC';
const RECENT_CYCLES = 10;
const CYCLE_MINUTES = 15;
const MINUTE = 60_000;

const notFound = (detail: string) => problem(404, 'Not Found', detail);

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

// A search the API refuses answers 400 with its reason, as the errors of the domain do (ADR 0027).
const refusedOr = (respond: () => Response): Response => {
  try {
    return respond();
  } catch (error) {
    if (error instanceof InvalidPeriod || error instanceof InvalidSearch) {
      return problem(400, 'Bad Request', error.message);
    }
    throw error;
  }
};

/** A page of a history of the tenant of the user, under the key the API gives it (R2.5.1, ADR 0138). */
const historyResponse = <T>(
  request: Request,
  rowsOf: (records: FakeRecords) => readonly FakeHistoryRow<T>[],
  key: string,
) =>
  withUser(request, (user) =>
    refusedOr(() => {
      const { found, next } = historyPage(rowsOf(user.records), new URL(request.url).searchParams);
      return HttpResponse.json({ [key]: found, next });
    }),
  );

// The stop answers with its outcome, the other commands with the flow (R1.1.4-R1.1.6).
const commandResponse = (flow: FakeFlow, command: FakeFlowCommand) =>
  command === 'stop'
    ? HttpResponse.json({ flow: flowResponse(flow), left_open: [] })
    : HttpResponse.json(flowResponse(flow));

// A refused configuration names its setting (R2.3.3); an unreadable request lists where and why, as the API does.
const configuring = async (
  request: Request,
  respond: (user: FakeUser, body: Record<string, unknown>) => FakeFlow,
  status = 200,
): Promise<Response> => {
  const body = (await request.json()) as Record<string, unknown>;
  return withUser(request, (user) => {
    try {
      return HttpResponse.json(flowResponse(respond(user, body)), { status });
    } catch (error) {
      if (error instanceof Refusal) {
        return problem(error.status, 'Refused', error.message, { field: error.field });
      }
      if (error instanceof InvalidRequest) {
        return problem(422, 'Unprocessable Entity', 'richiesta non valida', {
          errors: [{ loc: ['body', error.field], msg: error.message, type: 'invalid' }],
        });
      }
      throw error;
    }
  });
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

// Only an active flow plans a next cycle, one interval after its last one (R1.7.3).
const nextCycleOf = (flow: FakeFlow, newest: FakeCycle | undefined): string | null => {
  if (flow.status !== 'attivo') {
    return null;
  }
  const last = newest === undefined ? Date.now() : Date.parse(newest.planned_at);
  return apiInstant(new Date(last + CYCLE_MINUTES * MINUTE));
};

// The API measures the return in the domain (ADR 0127): the fake answers with the same figure, two decimals.
const returnPercentOf = (flow: FakeFlow): string | null => {
  const initial = flow.allocatedCapital ?? 0;
  return initial === 0 ? null : (((flow.currentCapital - initial) / initial) * 100).toFixed(2);
};

// A draft has no account yet: its name is empty, as on the API (ADR 0124).
const accountNameOf = (user: FakeUser, flow: FakeFlow): string =>
  user.accounts.find((account) => account.id === flow.accountId)?.name ?? '';

const outcomeOf = (cycle: FakeCycle) => ({ planned_at: cycle.planned_at, outcome: cycle.outcome });

const overviewOf = (user: FakeUser, flow: FakeFlow) => {
  const recent = newestFirst(fakePlatform.cyclesOf(flow.id)).slice(0, RECENT_CYCLES);
  const newest = recent[0];
  return {
    id: flow.id,
    name: flow.name,
    account: accountNameOf(user, flow),
    environment: 'dev',
    status: flow.status,
    pause_reason: flow.pauseReason,
    model: flow.model,
    version: flow.version,
    last_cycle: newest === undefined ? null : outcomeOf(newest),
    next_cycle_at: nextCycleOf(flow, newest),
    // A draft has no account yet, so no currency nor capital (ADR 0124).
    ...(flow.status === 'bozza'
      ? { currency: null, initial_capital: null, current_capital: null }
      : {
          currency: CURRENCY,
          initial_capital: String(flow.allocatedCapital ?? 0),
          current_capital: String(flow.currentCapital),
        }),
    return_percent: returnPercentOf(flow),
    recent_outcomes: recent.map(outcomeOf),
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
  status: flow.status,
  ...configurationOf(flow),
});

/** As the API names the file after the flow: a plain name for every client, the full one encoded (RFC 6266). */
const attachmentOf = (flowName: string): string => {
  const fileName = `${flowName}.json`;
  const plain = fileName.replace(/[^A-Za-z0-9 ._-]/g, '_');
  return `attachment; filename="${plain}"; filename*=UTF-8''${encodeURIComponent(fileName)}`;
};

type AssignmentRequest = { account_id: string; allocated_capital: string; assets?: string[] };

export const handlers = [
  ...accountHandlers,
  ...providerKeyHandlers,
  http.get('*/me', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({ user_id: user.account, tenant_id: user.tenantId }),
    ),
  ),
  // Archived flows answer only when asked for, as on the API (R1.1.6).
  http.get('*/flows', ({ request }) =>
    withUser(request, (user) => {
      const archived = new URL(request.url).searchParams.get('archived') === 'true';
      const listed = user.flows.filter((flow) => (flow.status === 'archiviato') === archived);
      return HttpResponse.json(listed.map(flowResponse));
    }),
  ),
  http.get('*/flows/overview', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json(
        user.flows
          .filter((flow) => flow.status !== 'archiviato')
          .map((flow) => overviewOf(user, flow)),
      ),
    ),
  ),
  http.get('*/history/cycles', ({ request }) =>
    historyResponse(request, (records) => records.cycles, 'cycles'),
  ),
  http.get('*/history/closed-positions', ({ request }) =>
    historyResponse(request, (records) => records.closedPositions, 'positions'),
  ),
  http.get('*/history/orders', ({ request }) =>
    historyResponse(request, (records) => records.orders, 'orders'),
  ),
  http.post('*/flows', ({ request }) => configuring(request, createFlow, 201)),
  http.patch('*/flows/:flowId', ({ request, params }) =>
    configuring(request, (user, body) => modifyFlow(user, String(params.flowId), body)),
  ),
  http.put('*/flows/:flowId/allocated-capital', ({ request, params }) =>
    configuring(request, (user, body) => changeAllocatedCapital(user, String(params.flowId), body)),
  ),
  http.get('*/models', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json({
        providers: [...new Set(FAKE_MODELS.map((model) => model.provider))].map((provider) => ({
          name: provider,
          key_registered: user.providerKeys.some((key) => key.provider === provider),
        })),
        models: FAKE_MODELS,
      }),
    ),
  ),
  http.get('*/sources', ({ request }) => withUser(request, () => HttpResponse.json(FAKE_SOURCES))),
  http.get('*/sources/:name', ({ request, params }) =>
    withUser(request, () => {
      const source = FAKE_SOURCES.find((candidate) => candidate.name === params.name);
      return source === undefined
        ? problem(404, 'Not Found', `fonte non disponibile: ${String(params.name)}`)
        : HttpResponse.json(source);
    }),
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
  http.get('*/flows/:flowId/strategy', ({ request, params }) =>
    withUser(request, (user) => {
      const { flowName, document } = fakePlatform.exportStrategy(user, String(params.flowId));
      return HttpResponse.json(document, {
        headers: { 'Content-Disposition': attachmentOf(flowName) },
      });
    }),
  ),
  http.post('*/flows/import', ({ request }) =>
    withUser(request, async (user) => {
      const document = (await request.json()) as FakeStrategyDocument;
      const name = new URL(request.url).searchParams.get('name') ?? '';
      return HttpResponse.json(flowResponse(fakePlatform.importStrategy(user, name, document)), {
        status: 201,
      });
    }),
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
  ...FAKE_FLOW_COMMANDS.map((command) =>
    http.post(`*/flows/:flowId/${command}`, ({ request, params }) =>
      withUser(request, (user) =>
        commandResponse(fakePlatform.command(user, String(params.flowId), command), command),
      ),
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
