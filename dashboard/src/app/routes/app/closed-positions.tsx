import { useParams, useSearchParams } from 'react-router';

import { ClosedPositions } from '@/features/flow-positions/components/closed-positions';
import { pageOf } from '@/utils/page-number';

/** The tab Posizioni chiuse of the page of the flow (R6.4.3). */
export const ClosedPositionsRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return <ClosedPositions flowId={flowId} page={pageOf(search.get('page'))} />;
};
