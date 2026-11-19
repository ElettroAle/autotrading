import { http, HttpResponse } from 'msw';

import { accountHandlers } from './account-handlers';
import { alertHandlers } from './alert-handlers';
import { capitalChangeHandlers } from './capital-changes';
import { FAKE_MODELS, FAKE_SOURCES, FAKE_SYSTEM_PROMPT, FAKE_TRADABLE_ASSETS } from './catalogs';
import { apiInstant, STEPS, summaryOf, type FakeCycle } from './cycles';
import { decisionPageOf, InvalidDecisionFilter } from './decisions';
import { emergencyClosingHandlers } from './emergency-closings';
import {
  changeAllocatedCapital,
  createFlow,
  InvalidRequest,
  modifyFlow,
  Refusal,
} from './flow-configuration';
import { rankingOf } from './flow-ranking';
import { resultsOf } from './flow-results';
import {
  contains,
  intervalWindowOf,
  InvalidPeriod,
  periodAdmits,
  statisticsOf,
} from './flow-statistics';
import { forecastAccuracyOf } from './forecast-accuracy';
import {
  closedPositionTotals,
  historyPage,
  InvalidSearch,
  orderTotals,
  type FakeHistoryRow,
  type FakeRecords,
} from './history';
import { lastDecisionOf } from './last-decision';
import { notificationChannelHandlers } from './notification-channel-handlers';
import { notificationEmailHandlers } from './notification-email-handlers';
import { notificationInboxHandlers } from './notification-inbox-handlers';
import {
  configurationOf,
  FAKE_FLOW_COMMANDS,
  fakePlatform,
  missingBeforeStartOf,
  type FakeFlowCommand,
  type FakeOpeningsResume,
  type FakeConfiguration,
  type FakeEquityPoint,
  type FakeFlow,
  type FakeStrategyDocument,
  type FakeUser,
} from './platform';
import type { FakeClosedPosition } from './positions';
import { API_KEY_FIELD, providerKeyHandlers } from './provider-key-handlers';
import { fakeReconciliation } from './reconciliation';
import { reconciliationHandlers } from './reconciliation-handlers';
import { problem, withUser } from './responses';

const NO_LINKED_CHAT = 'nessuna chat collegata';

/** The text of the test notification of R1.8.1, the same from the chat and from the dashboard. */
export const TEST_NOTIFICATION = 'notifica di prova: le notifiche dei tuoi flussi arrivano qui';

const CYCLES_PER_PAGE = 50;
const CLOSED_POSITIONS_PER_PAGE = 50;
const CURRENCY = 'USDC';
const RECENT_CYCLES = 10;
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
    max_total_margin_exposure_percent: null,
    max_total_value_exposure_percent: null,
  },
  default_stop_loss_percent: configuration.defaultStopLossPercent,
  default_take_profit_percent: configuration.defaultTakeProfitPercent,
  minimum_confidence: configuration.minimumConfidence,
  allocated_capital: configuration.allocatedCapital,
  bring_to_minimum: false,
  system_prompt: configuration.systemPrompt ?? FAKE_SYSTEM_PROMPT.system_prompt,
  system_prompt_is_default: configuration.systemPrompt === null,
  max_consecutive_failures: configuration.maxConsecutiveFailures,
  max_daily_loss_percent: configuration.maxDailyLossPercent,
  max_drawdown_percent: configuration.maxDrawdownPercent,
  openings_resume: configuration.openingsResume,
});

// A search the API refuses answers 400 with its reason, as the errors of the domain do (ADR 0027).
const refusedOr = (respond: () => Response): Response => {
  try {
    return respond();
  } catch (error) {
    if (
      error instanceof InvalidPeriod ||
      error instanceof InvalidSearch ||
      error instanceof InvalidDecisionFilter
    ) {
      return problem(400, 'Bad Request', error.message);
    }
    throw error;
  }
};

/**
 * A page of a history of the tenant of the user, under the key the API gives it (R2.5.1, ADR 0138); a history with
 * totals gives them with its first page only, those of every row of the search (Bug 569).
 */
const historyResponse = <T>(
  request: Request,
  rowsOf: (records: FakeRecords) => readonly FakeHistoryRow<T>[],
  key: string,
  totalsOf?: (admitted: T[]) => object,
) =>
  withUser(request, (user) =>
    refusedOr(() => {
      const search = new URL(request.url).searchParams;
      const { found, next, admitted } = historyPage(rowsOf(user.records), search);
      if (totalsOf === undefined) {
        return HttpResponse.json({ [key]: found, next });
      }
      const totals = search.has('after') ? null : totalsOf(admitted);
      return HttpResponse.json({ [key]: found, next, totals });
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

// The currency of the account of the flow; a draft has none, and answers no state (ADR 0124).
const currencyOf = (user: FakeUser, flow: FakeFlow): string =>
  user.accounts.find((account) => account.id === flow.accountId)?.currency ?? CURRENCY;

// The openings of every flow of an account with an open alarm of reconciliation are suspended (R3.3.1).
const alarmSuspensionOf = (user: FakeUser, flow: FakeFlow) => {
  const account = user.accounts.find((candidate) => candidate.id === flow.accountId);
  return account === undefined
    ? null
    : fakeReconciliation.openingsSuspensionOf(account.id, account.name);
};

// One suspension of the openings, the maximum loss first since the user can resume it (R3.2.2, R3.3.1).
const openingsSuspensionOf = (user: FakeUser, flow: FakeFlow) =>
  flow.openingsSuspension === null
    ? alarmSuspensionOf(user, flow)
    : {
        reason: flow.openingsSuspension.reason,
        suspended_at: flow.openingsSuspension.suspendedAt,
        cause: 'perdita_massima' as const,
        resumable: true,
      };

// The next cycle does not depend on the period: the summary gives the same instant as the overview (R6.4.8).
const resultsSummaryOf = (flow: FakeFlow, request: Request) => ({
  ...resultsOf(
    flow,
    fakePlatform.cyclesOf(flow.id),
    fakePlatform.openPositionsOf(flow.id).length,
    new URL(request.url).searchParams,
  ),
  next_cycle_at: nextCycleOf(flow),
});

const flowState = (user: FakeUser, flow: FakeFlow, request: Request) => ({
  flow_id: flow.id,
  currency: currencyOf(user, flow),
  allocated_capital: String(flow.allocatedCapital ?? 0),
  available_liquidity: '300',
  margin: '200',
  unrealized_pnl: '12',
  realized_pnl: '0',
  fees: '0',
  total_value: String(flow.currentCapital),
  return_percent: '2.4',
  positions: fakePlatform.openPositionsOf(flow.id),
  summary: resultsSummaryOf(flow, request),
  openings_suspension: openingsSuspensionOf(user, flow),
});

// The API counts a position won or lost by its result after the fees, as the statistics do (R6.4.4).
const resultOf = (position: FakeClosedPosition): string | undefined => {
  const net = Number(position.pnl) - Number(position.fees);
  if (net > 0) {
    return 'vinta';
  }
  return net < 0 ? 'persa' : undefined;
};

/** Whether the value of the row passes the filter of the query string with the name: a filter not asked admits it. */
const admits = (request: Request, name: string, value: string | undefined): boolean => {
  const asked = new URL(request.url).searchParams.get(name);
  return asked === null || asked === value;
};

// The instants of the query string, to the minute, as the lists of the API read them (R6.4.4, ADR periodo-al-minuto): a
// missing instant does not limit its side.
const admitsInterval = (request: Request, instant: string): boolean => {
  const search = new URL(request.url).searchParams;
  return contains(intervalWindowOf(search.get('from'), search.get('to')), new Date(instant));
};

const closedPositionPage = (positions: FakeClosedPosition[], request: Request) => {
  const page = pageOf(request);
  const start = (page - 1) * CLOSED_POSITIONS_PER_PAGE;
  const sorted = positions
    .filter(
      (position) =>
        admits(request, 'asset', position.asset) &&
        admits(request, 'side', position.side) &&
        admits(request, 'result', resultOf(position)) &&
        admitsInterval(request, position.closed_at),
    )
    .sort((one, other) => Date.parse(other.closed_at) - Date.parse(one.closed_at));
  return {
    page,
    has_next: sorted.length > start + CLOSED_POSITIONS_PER_PAGE,
    total: sorted.length,
    positions: sorted.slice(start, start + CLOSED_POSITIONS_PER_PAGE),
  };
};

// Only an active flow plans a next cycle, one interval after its last planned one: a cycle asked for now leaves the
// schedule as it is (R1.7.3, R6.5.2).
const nextCycleOf = (flow: FakeFlow): string | null => {
  if (flow.status !== 'attivo') {
    return null;
  }
  const planned = newestFirst(fakePlatform.cyclesOf(flow.id)).find(
    (cycle) => cycle.trigger === 'scheduled',
  );
  const last = planned === undefined ? Date.now() : Date.parse(planned.planned_at);
  return apiInstant(new Date(last + flow.cycleMinutes * MINUTE));
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

const overviewOf = (user: FakeUser, flow: FakeFlow, request: Request) => {
  const recent = newestFirst(fakePlatform.cyclesOf(flow.id)).slice(0, RECENT_CYCLES);
  const newest = recent[0];
  return {
    id: flow.id,
    name: flow.name,
    account: accountNameOf(user, flow),
    environment: 'dev',
    status: flow.status,
    pause_reason: flow.pauseReason,
    openings_suspension: openingsSuspensionOf(user, flow),
    model: flow.model,
    version: flow.version,
    last_cycle: newest === undefined ? null : outcomeOf(newest),
    next_cycle_at: nextCycleOf(flow),
    // A draft has no account yet, so no currency nor capital (ADR 0124).
    ...(flow.status === 'bozza'
      ? { currency: null, initial_capital: null, current_capital: null, summary: null }
      : {
          currency: currencyOf(user, flow),
          initial_capital: String(flow.allocatedCapital ?? 0),
          current_capital: String(flow.currentCapital),
          summary: resultsSummaryOf(flow, request),
        }),
    return_percent: returnPercentOf(flow),
    recent_outcomes: recent.map(outcomeOf),
  };
};

// The decisions as the user filters them, from the actions the journal of the cycle records (R6.4.4).
const DECISIONS: Record<string, string> = {
  apri: 'apertura',
  chiudi: 'chiusura',
  mantieni: 'mantenimento',
};

const decisionsOf = (cycle: FakeCycle): string[] => {
  const content = cycle.documents.find(
    (document) => document.step === STEPS.agentDecision,
  )?.content;
  const decisions = (content?.decisioni ?? []) as { action?: string }[];
  return decisions.map((decision) => DECISIONS[decision.action ?? ''] ?? '');
};

const admitsDecision = (request: Request, cycle: FakeCycle): boolean => {
  const asked = new URL(request.url).searchParams.get('decision');
  const decisions = decisionsOf(cycle);
  if (asked === null) {
    return true;
  }
  return asked === 'nessuna' ? decisions.length === 0 : decisions.includes(asked);
};

const cyclePage = (cycles: FakeCycle[], request: Request) => {
  const page = pageOf(request);
  const start = (page - 1) * CYCLES_PER_PAGE;
  const sorted = newestFirst(cycles).filter(
    (cycle) =>
      admits(request, 'outcome', cycle.outcome) &&
      admitsDecision(request, cycle) &&
      admitsInterval(request, cycle.planned_at),
  );
  return {
    page,
    has_next: sorted.length > start + CYCLES_PER_PAGE,
    total: sorted.length,
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

// The change of each point from the first point of the period, in percent with two decimals (ADR 0137).
const changeText = (equity: number, first: number): string | null =>
  first === 0 ? null : (((equity - first) / first) * 100).toFixed(2);

const equityResponse = (flow: FakeFlow, admits: (instant: Date) => boolean) => {
  const points = flow.equity
    .filter((point: FakeEquityPoint) => admits(point.plannedAt))
    .toSorted((first, second) => first.plannedAt.getTime() - second.plannedAt.getTime());
  const first = points[0]?.equity ?? 0;
  return {
    // A draft has no capital, and no cycle yet (ADR 0124).
    initial_capital: flow.allocatedCapital === null ? null : String(flow.allocatedCapital),
    points: points.map((point) => ({
      planned_at: point.plannedAt.toISOString(),
      equity: String(point.equity),
      change_percent: changeText(point.equity, first),
    })),
  };
};

const percentText = (percent: string | null): string =>
  percent === null ? 'nessuno' : `${percent}%`;

const RESUME_LABELS: Readonly<Record<FakeOpeningsResume, string>> = {
  manual: 'manuale',
  next_day: 'il giorno dopo',
};

// The parts the API compares, with the same names and texts (R1.1.3): the fake never compares in another way.
const PARTS: [string, (configuration: FakeConfiguration) => string][] = [
  ['asset', (configuration) => configuration.assets.join(', ')],
  ['intervallo di ciclo', (configuration) => `${configuration.cycleMinutes} minuti`],
  ['modello', (configuration) => configuration.model],
  ['istruzioni', (configuration) => configuration.instructions],
  ['leva massima', (configuration) => String(configuration.maxLeverage)],
  ['capitale allocato', (configuration) => configuration.allocatedCapital],
  ['system prompt', (configuration) => configuration.systemPrompt ?? 'predefinito'],
  [
    'cicli falliti consecutivi massimi',
    (configuration) => String(configuration.maxConsecutiveFailures ?? 'nessuno'),
  ],
  [
    'perdita giornaliera massima',
    (configuration) => percentText(configuration.maxDailyLossPercent),
  ],
  ['perdita massima dal picco', (configuration) => percentText(configuration.maxDrawdownPercent)],
  ['ripresa delle aperture', (configuration) => RESUME_LABELS[configuration.openingsResume]],
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
  missing: missingBeforeStartOf(flow),
});

/** As the API names the file after the flow: a plain name for every client, the full one encoded (RFC 6266). */
const attachmentOf = (flowName: string): string => {
  const fileName = `${flowName}.json`;
  const plain = fileName.replace(/[^A-Za-z0-9 ._-]/g, '_');
  return `attachment; filename="${plain}"; filename*=UTF-8''${encodeURIComponent(fileName)}`;
};

export const handlers = [
  // Before the routes of one flow, as on the API: the fixed path is not the identifier of a flow (R3.2.3).
  ...emergencyClosingHandlers,
  ...accountHandlers,
  ...reconciliationHandlers,
  ...alertHandlers,
  ...providerKeyHandlers,
  ...notificationEmailHandlers,
  ...notificationChannelHandlers,
  ...notificationInboxHandlers,
  ...capitalChangeHandlers,
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
      refusedOr(() =>
        HttpResponse.json(
          user.flows
            .filter((flow) => flow.status !== 'archiviato')
            .map((flow) => overviewOf(user, flow, request)),
        ),
      ),
    ),
  ),
  http.get('*/history/cycles', ({ request }) =>
    historyResponse(request, (records) => records.cycles, 'cycles'),
  ),
  http.get('*/history/closed-positions', ({ request }) =>
    historyResponse(
      request,
      (records) => records.closedPositions,
      'positions',
      closedPositionTotals,
    ),
  ),
  http.get('*/history/orders', ({ request }) =>
    historyResponse(request, (records) => records.orders, 'orders', orderTotals),
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
          key_fields: [API_KEY_FIELD],
        })),
        models: FAKE_MODELS,
      }),
    ),
  ),
  http.get('*/assets', ({ request }) =>
    withUser(request, () => HttpResponse.json(FAKE_TRADABLE_ASSETS)),
  ),
  http.get('*/sources', ({ request }) => withUser(request, () => HttpResponse.json(FAKE_SOURCES))),
  http.get('*/flows/system-prompt', ({ request }) =>
    withUser(request, () => HttpResponse.json(FAKE_SYSTEM_PROMPT)),
  ),
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
      HttpResponse.json(cyclePage(fakePlatform.cyclesOf(flow.id), request)),
    ),
  ),
  http.post('*/flows/:flowId/cycles', ({ request, params }) =>
    withUser(request, (user) =>
      HttpResponse.json(summaryOf(fakePlatform.runCycleNow(user, String(params.flowId))), {
        status: 201,
      }),
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
  http.get('*/flows/:flowId/decisions', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      refusedOr(() =>
        HttpResponse.json(
          decisionPageOf(fakePlatform.cyclesOf(flow.id), new URL(request.url).searchParams),
        ),
      ),
    ),
  ),
  http.get('*/flows/:flowId/decisions/latest', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      HttpResponse.json(lastDecisionOf(fakePlatform.cyclesOf(flow.id))),
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
  http.get('*/flows/ranking', ({ request }) =>
    withUser(request, (user) => {
      try {
        return HttpResponse.json(rankingOf(user.flows, new URL(request.url).searchParams));
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
  http.get('*/flows/:flowId/forecast-accuracy', ({ request, params }) =>
    withUser(request, (user) => {
      const flow = user.flows.find((candidate) => candidate.id === params.flowId);
      if (flow === undefined) {
        return problem(404, 'Not Found', 'flusso non trovato');
      }
      try {
        return HttpResponse.json(
          forecastAccuracyOf(flow.forecasts, new URL(request.url).searchParams),
        );
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
  // Only suspended openings resume, with the reason of the API otherwise (R3.2.2).
  http.post('*/flows/:flowId/openings/resume', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) => {
      if (flow.openingsSuspension === null) {
        return problem(409, 'Conflict', `le aperture di ${flow.name} non sono sospese`);
      }
      flow.openingsSuspension = null;
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.post('*/flows/:flowId/cash-out', async ({ request, params }) => {
    const body = (await request.json().catch(() => ({}))) as { capital?: string | null };
    const capital =
      body.capital === undefined || body.capital === null ? undefined : Number(body.capital);
    return withUser(request, (user) => {
      const { flow, freed } = fakePlatform.cashOut(user, String(params.flowId), capital);
      return HttpResponse.json({
        flow: flowResponse(flow),
        freed: String(freed),
        capital: String(flow.allocatedCapital),
        left_open: [],
      });
    });
  }),
  http.get('*/flows/:flowId/state', ({ request, params }) =>
    withUser(request, (user) => {
      const flow = user.flows.find((candidate) => candidate.id === params.flowId);
      return flow === undefined
        ? notFound('flusso non trovato')
        : refusedOr(() => HttpResponse.json(flowState(user, flow, request)));
    }),
  ),
  http.get('*/flows/:flowId/closed-positions', ({ request, params }) =>
    withFlow(request, params.flowId, (flow) =>
      HttpResponse.json(closedPositionPage(fakePlatform.closedPositionsOf(flow.id), request)),
    ),
  ),
];
