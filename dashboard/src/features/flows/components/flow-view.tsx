import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isRealMoney, TestNetworkNotice } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';

import { useAccounts } from '../api/get-accounts';
import { DRAFT_STATUS, useFlows, type Flow } from '../api/get-flows';

import { OpeningsSuspendedNotice } from './openings-suspended-notice';
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

type FlowViewProps = {
  readonly flowId: string;
  /** What the page offers on the flow once read, composed by the app from other features; realMoney says whether its
   * account trades on an exchange configured on real money (Bug 277). */
  readonly renderCommands: (flow: Flow, realMoney: boolean) => ReactNode;
  /** What follows the head of the flow once read: the period, the tabs and the tab chosen (R6.4.3). */
  readonly children?: ReactNode;
};

/**
 * The head of the page of the flow: its status with the commands of the status, the warning of the network and the
 * openings suspended (R3.3.2), then the command Configurazione, which holds what does not depend on the period (R6.4.3, ADR
 * pagina-del-flusso-a-schede-sotto-un-periodo-comune).
 */
export const FlowView = ({ flowId, renderCommands, children }: FlowViewProps) => {
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
  const account = accounts.data?.find((candidate) => candidate.id === flow.account_id);
  const realMoney = isRealMoney(account?.network);
  return (
    <>
      <section aria-label={flow.name} className="mb-4 rounded border border-slate-200 bg-white p-4">
        <div className="space-y-2">
          <FlowStatus flow={flow} />
          {account !== undefined && !realMoney ? (
            <TestNetworkNotice subject="Il flusso" networkName={account.network_name} />
          ) : null}
          {flow.status === DRAFT_STATUS ? null : <OpeningsSuspendedNotice flowId={flow.id} />}
        </div>
        {flow.status === DRAFT_STATUS ? (
          <div className="mt-3">
            <StartFlowButton flowId={flow.id} realMoney={realMoney} />
          </div>
        ) : (
          renderCommands(flow, realMoney)
        )}
        <div className="mt-3">
          <Link to={paths.flowVersions.getHref(flow.id)} className={SECONDARY_COMMAND}>
            Configurazione
          </Link>
        </div>
      </section>
      {children}
    </>
  );
};
