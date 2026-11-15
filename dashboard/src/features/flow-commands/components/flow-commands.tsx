import { useState } from 'react';
import { useNavigate } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { RealMoneyStartConfirmation } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';

import { useRunFlowCommand } from '../api/run-flow-command';
import { commandsAllowedIn, type FlowCommand } from '../utils/flow-transitions';

import { ArchiveConfirmation, StopConfirmation } from './command-confirmation';

const LABELS: Readonly<Record<FlowCommand, string>> = {
  start: 'Avvia',
  pause: 'Pausa',
  resume: 'Riprendi',
  stop: 'Stop',
  archive: 'Archivia',
};

type ConfirmedCommand = Extract<FlowCommand, 'stop' | 'archive' | 'start'>;

// The stop closes the positions and the archiving is final: both run only once the user confirms (ADR 0132). A start
// on an account that trades real money is confirmed too (Bug 277).
const needsConfirmation = (command: FlowCommand, realMoney: boolean): command is ConfirmedCommand =>
  command === 'stop' || command === 'archive' || (command === 'start' && realMoney);

type FlowCommandsProps = {
  readonly flowId: string;
  readonly status: string;
  readonly realMoney: boolean;
};

/** The commands the status of the flow admits, with the reason of a command the API refuses (R2.3.4). */
export const FlowCommands = ({ flowId, status, realMoney }: FlowCommandsProps) => {
  const [confirming, setConfirming] = useState<ConfirmedCommand | null>(null);
  const navigate = useNavigate();
  const run = useRunFlowCommand(flowId, {
    onSuccess: (command) => {
      // An archived flow is no longer among the flows in use: its page would find nothing.
      if (command === 'archive') {
        void navigate(paths.home.getHref());
      }
    },
  });

  const request = (command: FlowCommand) => {
    if (needsConfirmation(command, realMoney)) {
      setConfirming(command);
      return;
    }
    run.mutate(command);
  };

  const confirm = (command: ConfirmedCommand) => {
    run.mutate(command, { onSettled: () => setConfirming(null) });
  };

  const confirmation = {
    pending: run.isPending,
    onCancel: () => setConfirming(null),
  };

  return (
    <div className="mt-3 space-y-2">
      {confirming === null && (
        <div role="group" aria-label="Comandi del flusso" className="flex gap-2">
          {commandsAllowedIn(status).map((command) => (
            <button
              key={command}
              type="button"
              onClick={() => request(command)}
              disabled={run.isPending}
              className="rounded border border-slate-300 px-3 py-1.5 disabled:opacity-50"
            >
              {LABELS[command]}
            </button>
          ))}
        </div>
      )}
      {confirming === 'stop' && (
        <StopConfirmation flowId={flowId} onConfirm={() => confirm('stop')} {...confirmation} />
      )}
      {confirming === 'start' && (
        <RealMoneyStartConfirmation onConfirm={() => confirm('start')} {...confirmation} />
      )}
      {confirming === 'archive' && (
        <ArchiveConfirmation onConfirm={() => confirm('archive')} {...confirmation} />
      )}
      {run.isError && <ErrorMessage error={run.error} prefix="Comando non riuscito" />}
    </div>
  );
};
