import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isRealMoney, TestNetworkNotice } from '@/components/ui/network-notice';
import { ViewTabs, type View } from '@/components/ui/view-tabs';
import { paths } from '@/config/paths';

import { useAccounts } from '../api/get-accounts';
import { DRAFT_STATUS, useFlows, type Flow } from '../api/get-flows';

import { DraftAssignmentForm } from './draft-assignment-form';
import { DuplicateFlowButton } from './duplicate-flow-button';
import { ExportStrategyButton } from './export-strategy-button';
import { FlowDetails } from './flow-details';
import { FlowResults } from './flow-results';
import { RecentCycles } from './recent-cycles';
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

// The views of the flow are pages of their own, apart from the commands that change it (R6.4.1).
const flowViews = (flowId: string): View[] => [
  { name: 'Posizioni aperte', to: paths.flowPositions.getHref(flowId) },
  { name: 'Posizioni chiuse', to: paths.flowClosedPositions.getHref(flowId) },
  { name: 'Cicli del flusso', to: paths.flowCycles.getHref(flowId) },
  { name: 'Versioni della configurazione', to: paths.flowVersions.getHref(flowId) },
];

type FlowViewProps = {
  readonly flowId: string;
  /** What the page offers on the flow once read, composed by the app from other features; realMoney says whether its
   * account trades on an exchange configured on real money (Bug 277). */
  readonly renderCommands: (flow: Flow, realMoney: boolean) => ReactNode;
};

export const FlowView = ({ flowId, renderCommands }: FlowViewProps) => {
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
  const accountsOfTenant = accounts.data ?? [];
  const account = accountsOfTenant.find((candidate) => candidate.id === flow.account_id);
  const realMoney = isRealMoney(account?.network);
  return (
    <section aria-label={flow.name} className="rounded border border-slate-200 bg-white p-4">
      {/* How the flow is doing comes before every detail; a draft has no account, so no results yet (R6.4.2). */}
      {flow.status === DRAFT_STATUS ? null : (
        <div className="mb-3">
          <FlowResults flowId={flow.id} />
        </div>
      )}
      <div className="space-y-2">
        <FlowStatus flow={flow} />
        {account !== undefined && !realMoney ? (
          <TestNetworkNotice subject="Il flusso" networkName={account.network_name} />
        ) : null}
      </div>
      <div className="mt-3">
        <ViewTabs label="Dati del flusso" views={flowViews(flow.id)} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Link to={paths.editFlow.getHref(flow.id)} className={SECONDARY_COMMAND}>
          Modifica la configurazione
        </Link>
        <DuplicateFlowButton flowId={flow.id} />
        <ExportStrategyButton flowId={flow.id} />
        {flow.status === DRAFT_STATUS ? (
          <StartFlowButton flowId={flow.id} realMoney={realMoney} />
        ) : null}
      </div>
      {renderCommands(flow, realMoney)}
      <RecentCycles flowId={flow.id} />
      <FlowDetails flow={flow} accounts={accountsOfTenant} />
      {flow.status === DRAFT_STATUS ? (
        <DraftAssignmentForm flowId={flow.id} accounts={accountsOfTenant} />
      ) : null}
    </section>
  );
};
