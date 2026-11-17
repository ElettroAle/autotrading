import { useState } from 'react';
import { useNavigate } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { ErrorMessage } from '@/components/ui/error-message';
import { paths } from '@/config/paths';

import { useRunFlowCommand } from '../api/run-flow-command';
import { isArchivable } from '../utils/flow-transitions';

import { ArchiveConfirmation } from './command-confirmation';

type ArchiveFlowCommandProps = { readonly flowId: string; readonly status: string };

/**
 * Archivia, offered for a stopped flow or a draft at the bottom of the settings of the flow, and run only once the user
 * confirms, as the archiving is final (ADR impostazioni-del-flusso-dall-ingranaggio, ADR 0132).
 */
export const ArchiveFlowCommand = ({ flowId, status }: ArchiveFlowCommandProps) => {
  const [confirming, setConfirming] = useState(false);
  const navigate = useNavigate();
  // An archived flow is no longer among the flows in use: its pages would find nothing.
  const run = useRunFlowCommand(flowId, { onSuccess: () => void navigate(paths.home.getHref()) });
  if (!isArchivable(status)) {
    return null;
  }
  return (
    <div className="space-y-2">
      {confirming ? (
        <ArchiveConfirmation
          pending={run.isPending}
          onConfirm={() => run.mutate('archive', { onSettled: () => setConfirming(false) })}
          onCancel={() => setConfirming(false)}
        />
      ) : (
        <CommandButton tone="destructive" onClick={() => setConfirming(true)}>
          Archivia
        </CommandButton>
      )}
      {run.isError && <ErrorMessage error={run.error} prefix="Archiviazione non riuscita" />}
    </div>
  );
};
