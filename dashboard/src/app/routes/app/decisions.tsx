import { useParams, useSearchParams } from 'react-router';

import { DecisionsTable } from '@/features/decisions/components/decisions-table';
import { FlowMemory } from '@/features/flow-memory/components/flow-memory';
import { pageOf } from '@/utils/page-number';

/**
 * The tab Decisioni of the page of the flow: the memory of the agent, closed until opened, then the decisions (R6.5.5,
 * R5.3.4).
 */
export const DecisionsRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <>
      <FlowMemory flowId={flowId} />
      <DecisionsTable flowId={flowId} page={pageOf(search.get('page'))} />
    </>
  );
};
