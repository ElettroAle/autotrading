import { useParams, useSearchParams } from 'react-router';

import { DecisionsTable } from '@/features/decisions/components/decisions-table';
import { pageOf } from '@/utils/page-number';

/** The tab Decisioni of the page of the flow (R6.5.5). */
export const DecisionsRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return <DecisionsTable flowId={flowId} page={pageOf(search.get('page'))} />;
};
