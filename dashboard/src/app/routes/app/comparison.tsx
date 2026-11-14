import { PageLayout } from '@/components/layouts/page-layout';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { EquityComparison } from '@/features/equity-comparison/components/equity-comparison';
import { useFlows } from '@/features/flows/api/get-flows';

// The names of the flows come from the flows of the user, so the comparison never names a flow of another tenant.
const ComparedFlows = () => {
  const flows = useFlows();
  if (flows.isPending) {
    return <Loading />;
  }
  if (flows.isError) {
    return <ErrorMessage error={flows.error} />;
  }
  return <EquityComparison flows={flows.data} />;
};

export const ComparisonRoute = () => (
  <PageLayout title="Confronto dei flussi">
    <PeriodSelector />
    <ComparedFlows />
  </PageLayout>
);
