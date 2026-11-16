import { useParams, useSearchParams } from 'react-router';

import { FlowCapitalChanges } from '@/features/capital-changes/components/flow-capital-changes';
import { pageOf } from '@/utils/page-number';

/** The tab Capitale of the page of the flow (R3.4.2). */
export const FlowCapitalRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return <FlowCapitalChanges flowId={flowId} page={pageOf(search.get('page'))} />;
};
