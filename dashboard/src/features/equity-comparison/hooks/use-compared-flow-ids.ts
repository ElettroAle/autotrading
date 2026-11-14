import { useSearchParams } from 'react-router';

/** The ranking lets the user choose up to five flows to compare (RF-23.08). */
export const MAX_COMPARED_FLOWS = 5;

/** The flows to compare, from the query string of the page (ADR 0136): the first five, each once. */
export const useComparedFlowIds = (): string[] => {
  const [search] = useSearchParams();
  return [...new Set(search.getAll('flow'))].slice(0, MAX_COMPARED_FLOWS);
};
