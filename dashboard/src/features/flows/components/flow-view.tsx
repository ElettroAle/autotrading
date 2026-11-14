import { Link } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';

import { useAccounts } from '../api/get-accounts';
import { DRAFT_STATUS, useFlows, type Flow } from '../api/get-flows';

import { DraftAssignmentForm } from './draft-assignment-form';
import { DuplicateFlowButton } from './duplicate-flow-button';
import { ExportStrategyButton } from './export-strategy-button';
import { FlowDetails } from './flow-details';
import { StartFlowButton } from './start-flow-button';

const FlowStatus = ({ flow }: { flow: Flow }) => {
  if (flow.status === DRAFT_STATUS) {
    return (
      <span className="rounded bg-amber-100 px-2 py-0.5 text-sm font-medium text-amber-900">
        Bozza
      </span>
    );
  }
  return <p className="text-slate-600">Stato: {flow.status}</p>;
};

export const FlowView = ({ flowId }: { flowId: string }) => {
  const flows = useFlows();
  const accounts = useAccounts();
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
  const accountsOfTenant = accounts.data ?? [];
  return (
    <section aria-labelledby="flow-name" className="rounded border border-slate-200 bg-white p-4">
      <h2 id="flow-name" className="text-xl font-semibold">
        {flow.name}
      </h2>
      <FlowStatus flow={flow} />
      <nav aria-label="Dati del flusso" className="mt-2 flex flex-wrap gap-4">
        <Link to={paths.flowPositions.getHref(flow.id)} className="text-blue-800 hover:underline">
          Posizioni aperte
        </Link>
        <Link
          to={paths.flowClosedPositions.getHref(flow.id)}
          className="text-blue-800 hover:underline"
        >
          Posizioni chiuse
        </Link>
        <Link to={paths.flowCycles.getHref(flow.id)} className="text-blue-800 hover:underline">
          Cicli del flusso
        </Link>
        <Link to={paths.flowVersions.getHref(flow.id)} className="text-blue-800 hover:underline">
          Versioni della configurazione
        </Link>
      </nav>
      <FlowDetails flow={flow} accounts={accountsOfTenant} />
      <div className="mt-4 flex gap-3">
        <DuplicateFlowButton flowId={flow.id} />
        <ExportStrategyButton flowId={flow.id} />
        {flow.status === DRAFT_STATUS ? <StartFlowButton flowId={flow.id} /> : null}
      </div>
      {flow.status === DRAFT_STATUS ? (
        <DraftAssignmentForm flowId={flow.id} accounts={accountsOfTenant} />
      ) : null}
    </section>
  );
};
