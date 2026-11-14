import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowState } from '../api/get-flow-state';

type CommandConfirmationProps = Omit<
  Parameters<typeof ConfirmationDialog>[0],
  'title' | 'confirmLabel' | 'children'
>;

// The positions come from the state of the flow read now: the stop closes every one of them (R1.1.5).
const PositionsToClose = ({ flowId }: { flowId: string }) => {
  const state = useFlowState(flowId);
  if (state.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (state.data === undefined) {
    return (
      <>
        <ErrorMessage error={state.error} />
        <p>Tutte le posizioni aperte del flusso saranno chiuse.</p>
      </>
    );
  }
  if (state.data.positions.length === 0) {
    return <p>Il flusso non ha posizioni aperte.</p>;
  }
  return (
    <ul className="list-disc pl-5">
      {state.data.positions.map((position) => (
        <li key={position.asset}>La posizione su {position.asset} sarà chiusa</li>
      ))}
    </ul>
  );
};

export const StopConfirmation = ({
  flowId,
  ...props
}: CommandConfirmationProps & { flowId: string }) => (
  <ConfirmationDialog title="Conferma dello stop" confirmLabel="Conferma lo stop" {...props}>
    <p>Il flusso smetterà di eseguire cicli.</p>
    <PositionsToClose flowId={flowId} />
  </ConfirmationDialog>
);

// Only a stopped flow is archived, and the stop has already closed its positions (R1.1.6).
export const ArchiveConfirmation = (props: CommandConfirmationProps) => (
  <ConfirmationDialog
    title="Conferma dell'archiviazione"
    confirmLabel="Conferma l'archiviazione"
    {...props}
  >
    <p>
      L&apos;archiviazione è definitiva: il flusso non si potrà più avviare né modificare. Un flusso
      fermo non ha posizioni aperte da gestire e il suo capitale allocato torna libero sul conto.
    </p>
  </ConfirmationDialog>
);
