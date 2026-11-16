import { http, HttpResponse } from 'msw';

import { apiInstant } from './cycles';
import { contains, intervalWindowOf } from './flow-statistics';
import { fakePlatform, type FakeCapitalChange, type FakeFlow } from './platform';
import { problem, withUser } from './responses';

const CAPITAL_CHANGES_PER_PAGE = 50;
const NOT_FOUND = 'non trovato';

/** A change of the capital of the flow, from the capital it had to the new one, at the instant (R1.1.7, R3.4.2). */
export const aCapitalChange = (
  flow: FakeFlow,
  previous: number,
  next: number,
  at: Date,
): FakeCapitalChange => ({
  accountId: flow.accountId ?? '',
  changed_at: apiInstant(at),
  flow_id: flow.id,
  flow: flow.name,
  reason: next > previous ? 'aumento' : 'riduzione',
  amount: String(Math.abs(next - previous)),
  previous: String(previous),
  new: String(next),
});

/** A cash-out of the flow that freed the amount and kept the capital, at the instant (R3.4.1, R3.4.3). */
export const aCashOut = (flow: FakeFlow, amount: number, at: Date): FakeCapitalChange => ({
  ...aCapitalChange(flow, flow.allocatedCapital ?? 0, flow.allocatedCapital ?? 0, at),
  reason: 'incasso',
  amount: String(amount),
});

/** A deposit or a withdrawal the exchange declares on the account, at the instant (R3.4.2). */
export const aTransfer = (
  accountId: string,
  reason: 'deposito' | 'prelievo',
  amount: number,
  at: Date,
): FakeCapitalChange => ({
  accountId,
  changed_at: apiInstant(at),
  flow_id: null,
  flow: null,
  reason,
  amount: String(amount),
  previous: null,
  new: null,
});

// The instants of the query string, to the minute, as the API reads them (ADR periodo-al-minuto): a missing instant
// does not limit its side.
const admitsInterval = (search: URLSearchParams, instant: string): boolean =>
  contains(intervalWindowOf(search.get('from'), search.get('to')), new Date(instant));

const answerOf = (change: FakeCapitalChange) => ({
  changed_at: change.changed_at,
  flow_id: change.flow_id,
  flow: change.flow,
  reason: change.reason,
  amount: change.amount,
  previous: change.previous,
  new: change.new,
});

const pageOf = (changes: FakeCapitalChange[], request: Request) => {
  const search = new URL(request.url).searchParams;
  const page = Number(search.get('page') ?? '1');
  const start = (page - 1) * CAPITAL_CHANGES_PER_PAGE;
  const sorted = changes
    .filter((change) => admitsInterval(search, change.changed_at))
    .sort((one, other) => Date.parse(other.changed_at) - Date.parse(one.changed_at));
  return {
    page,
    has_next: sorted.length > start + CAPITAL_CHANGES_PER_PAGE,
    total: sorted.length,
    currency: 'USDC',
    changes: sorted.slice(start, start + CAPITAL_CHANGES_PER_PAGE).map(answerOf),
  };
};

/** The history of the capital of a flow and of an account, as the API pages it (R3.4.2). */
export const capitalChangeHandlers = [
  http.get('*/flows/:flowId/capital-changes', ({ request, params }) =>
    withUser(request, (user) => {
      const flow = user.flows.find((candidate) => candidate.id === params.flowId);
      if (flow === undefined) {
        return problem(404, 'Not Found', NOT_FOUND);
      }
      const changes = fakePlatform
        .capitalChangesOfAccount(flow.accountId ?? '')
        .filter((change) => change.flow_id === flow.id);
      return HttpResponse.json(pageOf(changes, request));
    }),
  ),
  http.get('*/accounts/:accountId/capital-changes', ({ request, params }) =>
    withUser(request, (user) => {
      const account = user.accounts.find((candidate) => candidate.id === params.accountId);
      if (account === undefined) {
        return problem(404, 'Not Found', NOT_FOUND);
      }
      return HttpResponse.json(pageOf(fakePlatform.capitalChangesOfAccount(account.id), request));
    }),
  ),
];
