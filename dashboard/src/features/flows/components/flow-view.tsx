import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { ErrorMessage } from '@/components/ui/error-message';
import { Icon } from '@/components/ui/icons/icon';
import { Loading } from '@/components/ui/loading';
import { isRealMoney, TestNetworkNotice } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';
import { ApiError } from '@/lib/api-client';

import { useAccounts } from '../api/get-accounts';
import { useFlow } from '../api/get-flow';
import { ARCHIVED_STATUS, DRAFT_STATUS, type Flow } from '../api/get-flows';

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

const NOT_FOUND = 404;

const isNotFound = (error: Error): boolean =>
  error instanceof ApiError && error.status === NOT_FOUND;

// A draft only starts; an archived flow is final, so its page offers no command (Bug 690).
const FlowCommandsOf = ({
  flow,
  realMoney,
  renderCommands,
}: {
  readonly flow: Flow;
  readonly realMoney: boolean;
  readonly renderCommands: FlowViewProps['renderCommands'];
}) => {
  if (flow.status === ARCHIVED_STATUS) {
    return null;
  }
  if (flow.status === DRAFT_STATUS) {
    return (
      <div className="mt-3">
        <StartFlowButton flowId={flow.id} realMoney={realMoney} missing={flow.missing} />
      </div>
    );
  }
  return renderCommands(flow, realMoney);
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
 * openings suspended (R3.3.2), with a gear at the top right that opens the settings of the flow, a page and not a tab,
 * so reading and writing do not mix (ADR impostazioni-del-flusso-dall-ingranaggio). The flow is read alone, so an
 * archived one opens too, in read only: no command and no gear (ADR pagina-del-flusso-archiviato-in-sola-lettura).
 */
export const FlowView = ({ flowId, renderCommands, children }: FlowViewProps) => {
  const read = useFlow(flowId);
  const accounts = useAccounts();
  if (read.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the flow already read on the page: the warning is the page's (ADR 0119).
  if (read.data === undefined) {
    return isNotFound(read.error) ? (
      <p>Flusso non trovato.</p>
    ) : (
      <ErrorMessage error={read.error} />
    );
  }
  const flow = read.data;
  const account = accounts.data?.find((candidate) => candidate.id === flow.account_id);
  const realMoney = isRealMoney(account?.network);
  return (
    <>
      <section aria-label={flow.name} className="mb-4 rounded border border-slate-200 bg-white p-4">
        {/* One gap between the status and the notice of the network, with no margin of their own (ADR
            spaziatura-tra-stato-e-avviso-della-rete). */}
        <div className="flex items-start gap-2">
          <div
            role="group"
            aria-label="Stato del flusso"
            className="flex flex-wrap items-center gap-2"
          >
            <FlowStatus flow={flow} />
            {account !== undefined && !realMoney ? (
              <TestNetworkNotice subject="Il flusso" networkName={account.network_name} />
            ) : null}
          </div>
          {flow.status === ARCHIVED_STATUS ? null : (
            <Link
              to={paths.flowSettings.getHref(flow.id)}
              aria-label="Impostazioni del flusso"
              title="Impostazioni del flusso"
              className={`${SECONDARY_COMMAND} ml-auto`}
            >
              <Icon name="settings" />
            </Link>
          )}
        </div>
        <FlowCommandsOf flow={flow} realMoney={realMoney} renderCommands={renderCommands} />
      </section>
      {children}
    </>
  );
};
