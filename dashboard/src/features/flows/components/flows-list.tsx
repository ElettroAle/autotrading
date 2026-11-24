import { Card } from '@/components/ui/card';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { usePeriod } from '@/components/ui/period-selector/use-period';

import { useFlowOverviews } from '../api/get-flow-overviews';

import { FlowOverviewCard } from './flow-overview-card';

/** The flows in use of the user, each at a glance, with its results in the period chosen above the list (R2.2.2, R6.4.2). */
export const FlowsList = () => {
  const [period] = usePeriod();
  const flows = useFlowOverviews(period);
  if (flows.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the flows already read on the page: the warning is the page's (ADR 0119).
  if (flows.data === undefined) {
    return <ErrorMessage error={flows.error} />;
  }
  if (flows.data.length === 0) {
    return <p>Non hai ancora flussi.</p>;
  }
  return (
    <ul aria-label="Flussi" className="space-y-3">
      {flows.data.map((flow) => (
        <Card as="li" key={flow.id}>
          <FlowOverviewCard flow={flow} />
        </Card>
      ))}
    </ul>
  );
};
