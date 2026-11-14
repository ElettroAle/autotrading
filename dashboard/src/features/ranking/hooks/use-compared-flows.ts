import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

/** At most five curves on the same chart (R2.4.3). */
export const MAX_COMPARED_FLOWS = 5;

const FLOWS = 'flows';
const SEPARATOR = ',';

const flowsOf = (search: URLSearchParams): string[] =>
  (search.get(FLOWS) ?? '').split(SEPARATOR).filter((flowId) => flowId !== '');

const withFlows = (current: URLSearchParams, flowIds: readonly string[]): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.delete(FLOWS);
  if (flowIds.length > 0) {
    next.set(FLOWS, flowIds.join(SEPARATOR));
  }
  return next;
};

// A flow chosen is left out again; a new one joins while fewer than five are chosen.
const toggled = (flowIds: readonly string[], flowId: string): string[] =>
  flowIds.includes(flowId)
    ? flowIds.filter((id) => id !== flowId)
    : [...flowIds, flowId].slice(0, MAX_COMPARED_FLOWS);

/** The query string of the comparison view: the period of the API and the flows chosen (ADR 0136). */
export const comparisonSearchOf = (periodSearch: string, flowIds: readonly string[]): string =>
  withFlows(new URLSearchParams(periodSearch), flowIds).toString();

/**
 * The flows chosen for the overlaid curves live in the query string, shared with the comparison view together with
 * the period (ADR 0136).
 */
export const useComparedFlows = (): [readonly string[], (flowId: string) => void] => {
  const [search, setSearch] = useSearchParams();
  const toggle = useCallback(
    (flowId: string) => {
      setSearch((current) => withFlows(current, toggled(flowsOf(current), flowId)));
    },
    [setSearch],
  );
  return [flowsOf(search), toggle];
};
