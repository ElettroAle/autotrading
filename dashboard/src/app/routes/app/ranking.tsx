import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowRanking } from '@/features/ranking/components/flow-ranking';

export const RankingRoute = () => (
  <DashboardLayout title="Classifica dei flussi">
    <PeriodSelector />
    <FlowRanking />
  </DashboardLayout>
);
