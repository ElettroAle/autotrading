import { useCallback } from 'react';
import { useSearchParams } from 'react-router';

import { useSearchChange } from '@/hooks/use-search-change';
import { comparedFlowsIn, MAX_COMPARED_FLOWS, withComparedFlows } from '@/utils/compared-flows';

// A flow chosen is left out again; a new one joins while fewer than five are chosen.
const toggled = (flowIds: readonly string[], flowId: string): string[] =>
  flowIds.includes(flowId)
    ? flowIds.filter((id) => id !== flowId)
    : [...flowIds, flowId].slice(0, MAX_COMPARED_FLOWS);

/**
 * The flows chosen for the overlaid curves live in the query string, in the same form as in the comparison view, so
 * the ranking hands them over together with the period (ADR 0136). Choices in quick succession add up (ADR 0166).
 */
export const useComparedFlows = (): [readonly string[], (flowId: string) => void] => {
  const [search] = useSearchParams();
  const changeSearch = useSearchChange();
  const toggle = useCallback(
    (flowId: string) => {
      changeSearch((current) =>
        withComparedFlows(current, toggled(comparedFlowsIn(current), flowId)),
      );
    },
    [changeSearch],
  );
  return [comparedFlowsIn(search), toggle];
};
