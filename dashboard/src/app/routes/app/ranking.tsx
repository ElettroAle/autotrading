import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { FlowViewTabs } from '@/features/flows/components/flow-view-tabs';
import { FlowRanking } from '@/features/ranking/components/flow-ranking';

// The ranking is a view of the flows, beside their list: it bears the same title (ADR 0161).
export const RankingRoute = () => (
  <DashboardLayout title="I tuoi flussi">
    <FlowViewTabs />
    <PeriodSelector />
    <FlowRanking />
  </DashboardLayout>
);
