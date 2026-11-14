/** At most five curves on the same chart (RF-23.08, R2.4.3). */
export const MAX_COMPARED_FLOWS = 5;

/** One parameter per compared flow, the same in the ranking and in the comparison (ADR 0136, ADR 0137). */
const COMPARED_FLOW = 'flow';

/** The compared flows of a query string: the first five, each once. */
export const comparedFlowsIn = (search: URLSearchParams): string[] =>
  [...new Set(search.getAll(COMPARED_FLOW).filter((flowId) => flowId !== ''))].slice(
    0,
    MAX_COMPARED_FLOWS,
  );

/** The query string with these compared flows in place of the previous ones, the other parameters untouched. */
export const withComparedFlows = (
  current: URLSearchParams,
  flowIds: readonly string[],
): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.delete(COMPARED_FLOW);
  flowIds.forEach((flowId) => next.append(COMPARED_FLOW, flowId));
  return next;
};
