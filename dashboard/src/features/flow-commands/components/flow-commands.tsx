import { useState } from 'react';
import { useNavigate } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
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

type ConfirmedCommand = Extract<FlowCommand, 'stop' | 'archive'>;

// The stop closes the positions and the archiving is final: both run only once the user confirms (ADR 0132).
const needsConfirmation = (command: FlowCommand): command is ConfirmedCommand =>
  command === 'stop' || command === 'archive';

type FlowCommandsProps = { readonly flowId: string; readonly status: string };

/** The commands the status of the flow admits, with the reason of a command the API refuses (R2.3.4). */
export const FlowCommands = ({ flowId, status }: FlowCommandsProps) => {
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
    if (needsConfirmation(command)) {
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
      {confirming === 'archive' && (
        <ArchiveConfirmation onConfirm={() => confirm('archive')} {...confirmation} />
      )}
      {run.isError && <ErrorMessage error={run.error} prefix="Comando non riuscito" />}
    </div>
  );
};
