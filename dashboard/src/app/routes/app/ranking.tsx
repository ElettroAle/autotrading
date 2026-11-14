import { PageLayout } from '@/components/layouts/page-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowRanking } from '@/features/ranking/components/flow-ranking';

export const RankingRoute = () => (
  <PageLayout title="Classifica dei flussi">
    <PeriodSelector />
    <FlowRanking />
  </PageLayout>
);
