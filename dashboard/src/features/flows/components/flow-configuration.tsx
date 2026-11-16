import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';

import { useAccounts } from '../api/get-accounts';
import { useFlows } from '../api/get-flows';

import { DuplicateFlowButton } from './duplicate-flow-button';
import { ExportStrategyButton } from './export-strategy-button';
import { FlowDetails } from './flow-details';

/**
 * What does not depend on the period, out of the tabs of the flow: the configuration in force and the commands that
 * edit, duplicate and export it (R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune).
 */
export const FlowConfiguration = ({ flowId }: { flowId: string }) => {
  const flows = useFlows();
  const accounts = useAccounts();
  if (flows.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the flow already read on the page: the warning is the page's (ADR 0119).
  if (flows.data === undefined) {
    return <ErrorMessage error={flows.error} />;
  }
  const flow = flows.data.find((candidate) => candidate.id === flowId);
  if (flow === undefined) {
    return <p>Flusso non trovato.</p>;
  }
  return (
    <section aria-label={flow.name} className="mb-4 rounded border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap gap-2">
        <Link to={paths.editFlow.getHref(flow.id)} className={SECONDARY_COMMAND}>
          Modifica
        </Link>
        <DuplicateFlowButton flowId={flow.id} />
        <ExportStrategyButton flowId={flow.id} />
      </div>
      <FlowDetails flow={flow} accounts={accounts.data ?? []} />
    </section>
  );
};
