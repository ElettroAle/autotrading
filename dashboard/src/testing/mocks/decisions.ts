import type { FakeCycle } from './cycles';
import { periodAdmits } from './flow-statistics';
import { COMPLETED, decisionResponse, decisionsOf } from './last-decision';

/**
 * The history of the decisions of a flow as the API gives it (ADR storico-delle-decisioni-nell-api): one decision by
 * completed cycle and asset in the period, newest first and then by asset, filtered by asset, action and direction, in
 * the pages of the cycles.
 */

const DECISIONS_PER_PAGE = 50;
const ACTIONS = ['apri', 'chiudi', 'mantieni', 'aggiorna'];
const DIRECTIONS = ['long', 'short'];

/** The answer of the API to a filter it rejects, with the reason it gives. */
export class InvalidDecisionFilter extends Error {}

type DecisionRow = ReturnType<typeof decisionResponse> & { readonly planned_at: string };

const checked = (search: URLSearchParams, name: string, choices: string[], what: string) => {
  const value = search.get(name);
  if (value !== null && !choices.includes(value)) {
    throw new InvalidDecisionFilter(`${what} non valida: scegliere tra ${choices.join(', ')}`);
  }
  return value;
};

const rowsOf = (cycle: FakeCycle): DecisionRow[] =>
  decisionsOf(cycle)
    .map((decision) => ({ planned_at: cycle.planned_at, ...decisionResponse(decision) }))
    .toSorted((one, other) => one.asset.localeCompare(other.asset));

export const decisionPageOf = (cycles: FakeCycle[], search: URLSearchParams) => {
  const action = checked(search, 'action', ACTIONS, 'azione');
  const direction = checked(search, 'direction', DIRECTIONS, 'direzione');
  const asset = search.get('asset');
  const admits = periodAdmits(search);
  const page = Number(search.get('page') ?? '1');
  const start = (page - 1) * DECISIONS_PER_PAGE;
  const matching = cycles
    .filter((cycle) => cycle.outcome === COMPLETED && admits(new Date(cycle.planned_at)))
    .toSorted((one, other) => Date.parse(other.planned_at) - Date.parse(one.planned_at))
    .flatMap(rowsOf)
    .filter(
      (row) =>
        (asset === null || row.asset === asset) &&
        (action === null || row.action === action) &&
        (direction === null || row.direction === direction),
    );
  return {
    page,
    has_next: matching.length > start + DECISIONS_PER_PAGE,
    total: matching.length,
    decisions: matching.slice(start, start + DECISIONS_PER_PAGE),
  };
};
