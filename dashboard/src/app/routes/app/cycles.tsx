import { useParams, useSearchParams } from 'react-router';

import { CyclesList } from '@/features/cycles/components/cycles-list';
import { pageOf } from '@/utils/page-number';

/** The tab Cicli of the page of the flow (R6.4.3). */
export const CyclesRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return <CyclesList flowId={flowId} page={pageOf(search.get('page'))} />;
};
