import { useSearchParams } from 'react-router';

import { comparedFlowsIn } from '@/utils/compared-flows';

/** The flows to compare, from the query string of the page (ADR 0136): the first five, each once. */
export const useComparedFlowIds = (): string[] => {
  const [search] = useSearchParams();
  return comparedFlowsIn(search);
};
