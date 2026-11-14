import { Link } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';

import { useFlows } from '../api/get-flows';

import { EquityCurve } from './equity-curve';

export const FlowView = ({ flowId }: { flowId: string }) => {
  const flows = useFlows();
  if (flows.isPending) {
    return <Loading />;
  }
  if (flows.isError) {
    return <ErrorMessage error={flows.error} />;
  }
  const flow = flows.data.find((candidate) => candidate.id === flowId);
  if (flow === undefined) {
    return <p>Flusso non trovato.</p>;
  }
  return (
    <>
      <section aria-labelledby="flow-name" className="rounded border border-slate-200 bg-white p-4">
        <h2 id="flow-name" className="text-xl font-semibold">
          {flow.name}
        </h2>
        <p className="text-slate-600">Stato: {flow.status}</p>
        <Link to={paths.flowCycles.getHref(flow.id)} className="text-blue-800 hover:underline">
          Cicli del flusso
        </Link>
      </section>
      <EquityCurve flowId={flow.id} />
    </>
  );
};
