import type { ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowState } from '../api/get-flow-state';

type ConfirmationProps = {
  readonly title: string;
  readonly confirmLabel: string;
  readonly pending: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly children: ReactNode;
};

const Confirmation = ({
  title,
  confirmLabel,
  pending,
  onConfirm,
  onCancel,
  children,
}: ConfirmationProps) => (
  <div role="group" aria-label={title} className="space-y-2">
    {children}
    <div className="flex gap-2">
      <button
        type="button"
        onClick={onConfirm}
        disabled={pending}
        className="rounded bg-red-700 px-3 py-1.5 text-white disabled:opacity-50"
      >
        {confirmLabel}
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded border border-slate-300 px-3 py-1.5"
      >
        Annulla
      </button>
    </div>
  </div>
);

type CommandConfirmationProps = Omit<ConfirmationProps, 'title' | 'confirmLabel' | 'children'>;

// The positions come from the state of the flow read now: the stop closes every one of them (R1.1.5).
const PositionsToClose = ({ flowId }: { flowId: string }) => {
  const state = useFlowState(flowId);
  if (state.isPending) {
    return <Loading />;
  }
  if (state.isError) {
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
  <Confirmation title="Conferma dello stop" confirmLabel="Conferma lo stop" {...props}>
    <p>Il flusso smetterà di eseguire cicli.</p>
    <PositionsToClose flowId={flowId} />
  </Confirmation>
);

// Only a stopped flow is archived, and the stop has already closed its positions (R1.1.6).
export const ArchiveConfirmation = (props: CommandConfirmationProps) => (
  <Confirmation
    title="Conferma dell'archiviazione"
    confirmLabel="Conferma l'archiviazione"
    {...props}
  >
    <p>
      L&apos;archiviazione è definitiva: il flusso non si potrà più avviare né modificare. Un flusso
      fermo non ha posizioni aperte da gestire e il suo capitale allocato torna libero sul conto.
    </p>
  </Confirmation>
);
