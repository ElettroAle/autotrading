import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowOverviews } from '../api/get-flow-overviews';

import { FlowOverviewCard } from './flow-overview-card';

/** The flows in use of the user, each at a glance (R2.2.2). */
export const FlowsList = () => {
  const flows = useFlowOverviews();
  if (flows.isPending) {
    return <Loading />;
  }
  if (flows.isError) {
    return <ErrorMessage error={flows.error} />;
  }
  if (flows.data.length === 0) {
    return <p>Non hai ancora flussi.</p>;
  }
  return (
    <ul
      aria-label="Flussi"
      className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
    >
      {flows.data.map((flow) => (
        <li key={flow.id} className="px-4 py-3">
          <FlowOverviewCard flow={flow} />
        </li>
      ))}
    </ul>
  );
};
