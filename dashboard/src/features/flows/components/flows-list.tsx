import { Link } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';

import { useFlows } from '../api/get-flows';

export const FlowsList = () => {
  const flows = useFlows();
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
        <li key={flow.id} className="flex items-center justify-between px-4 py-3">
          <Link
            to={paths.flow.getHref(flow.id)}
            className="font-medium text-blue-800 hover:underline"
          >
            {flow.name}
          </Link>
          <span className="text-sm text-slate-600">{flow.status}</span>
        </li>
      ))}
    </ul>
  );
};
