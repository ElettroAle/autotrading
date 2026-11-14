import { useParams, useSearchParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { CyclesList } from '@/features/cycles/components/cycles-list';

const FIRST_PAGE = 1;

// The page lives in the query string, so a page of the list has a link of its own; anything else is the first page.
const pageOf = (value: string | null): number => {
  const page = Number(value);
  return Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE;
};

export const CyclesRoute = () => {
  const { flowId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <PageLayout title="Cicli del flusso">
      <CyclesList flowId={flowId} page={pageOf(search.get('page'))} />
    </PageLayout>
  );
};
