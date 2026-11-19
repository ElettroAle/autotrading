import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { SourceTrialsList } from '@/features/source-trials/components/source-trials-list';

// The sources of the catalog with the trial of each adapter, apart from the flows (ADR pagina-fonti-con-la-prova).
export const SourcesRoute = () => (
  <DashboardLayout title="Fonti">
    <SourceTrialsList />
  </DashboardLayout>
);
