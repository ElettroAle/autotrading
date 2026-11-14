import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { comparedFlowsIn, MAX_COMPARED_FLOWS, withComparedFlows } from '@/utils/compared-flows';

// A flow chosen is left out again; a new one joins while fewer than five are chosen.
const toggled = (flowIds: readonly string[], flowId: string): string[] =>
  flowIds.includes(flowId)
    ? flowIds.filter((id) => id !== flowId)
    : [...flowIds, flowId].slice(0, MAX_COMPARED_FLOWS);

/**
 * The flows chosen for the overlaid curves live in the query string, in the same form as in the comparison view, so
 * the ranking hands them over together with the period (ADR 0136).
 */
export const useComparedFlows = (): [readonly string[], (flowId: string) => void] => {
  const [search, setSearch] = useSearchParams();
  const toggle = useCallback(
    (flowId: string) => {
      setSearch((current) => withComparedFlows(current, toggled(comparedFlowsIn(current), flowId)));
    },
    [setSearch],
  );
  return [comparedFlowsIn(search), toggle];
};
