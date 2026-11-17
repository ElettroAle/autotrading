import { useState } from 'react';

import { DESTRUCTIVE_COMMAND, SECONDARY_COMMAND } from '@/components/ui/commands';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useCloseInEmergency } from '../api/close-in-emergency';
import { useEmergencyClosingPreview } from '../api/get-emergency-closing-preview';
import type { EmergencyScope } from '../types/emergency-scope';
import { emergencyQuestion } from '../utils/emergency-question';

import { EmergencyClosingOutcome } from './emergency-closing-outcome';

type ConfirmationProps = {
  readonly scope: EmergencyScope;
  readonly pending: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
};

// The question names the positions the API counts now; nothing closes before the user confirms.
const Confirmation = ({ scope, pending, onConfirm, onCancel }: ConfirmationProps) => {
  const preview = useEmergencyClosingPreview(scope, true);
  if (preview.isError) {
    return (
      <div className="space-y-2">
        <ErrorMessage error={preview.error} prefix="Chiusura di emergenza non disponibile" />
        <button type="button" onClick={onCancel} className={SECONDARY_COMMAND}>
          Annulla
        </button>
      </div>
    );
  }
  if (preview.data === undefined) {
    return <Loading />;
  }
  return (
    <ConfirmationDialog
      title="Conferma della chiusura di emergenza"
      confirmLabel="Chiudi e metti in pausa"
      pending={pending}
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <p>{emergencyQuestion(scope, preview.data.positions)}</p>
    </ConfirmationDialog>
  );
};

/**
 * The emergency closing of a flow, of the flows of an account or of every flow: one command for the three scopes,
 * which the pages compose (ADR chiusura-di-emergenza-nella-dashboard).
 */
export const EmergencyClosingCommand = ({ scope }: { readonly scope: EmergencyScope }) => {
  const [confirming, setConfirming] = useState(false);
  const closing = useCloseInEmergency(scope);

  const open = () => {
    closing.reset();
    setConfirming(true);
  };

  const confirm = () => {
    closing.mutate(undefined, { onSettled: () => setConfirming(false) });
  };

  return (
    <div className="space-y-2">
      {!confirming && (
        <button
          type="button"
          onClick={open}
          disabled={closing.isPending}
          className={DESTRUCTIVE_COMMAND}
        >
          Chiusura di emergenza
        </button>
      )}
      {confirming && (
        <Confirmation
          scope={scope}
          pending={closing.isPending}
          onConfirm={confirm}
          onCancel={() => setConfirming(false)}
        />
      )}
      {closing.isSuccess && <EmergencyClosingOutcome closing={closing.data} />}
      {closing.isError && (
        <ErrorMessage error={closing.error} prefix="Chiusura di emergenza non riuscita" />
      )}
    </div>
  );
};
