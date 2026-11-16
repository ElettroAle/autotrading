import { useState } from 'react';

import { CommandRefusal } from '@/components/ui/command-refusal';
import { PRIMARY_COMMAND } from '@/components/ui/commands';
import { RealMoneyStartConfirmation } from '@/components/ui/network-notice';

import { useStartFlow } from '../api/start-flow';

type StartFlowButtonProps = { readonly flowId: string; readonly realMoney: boolean };

/** Starts a draft; on an account that trades real money only once the user confirms it (Bug 277). */
export const StartFlowButton = ({ flowId, realMoney }: StartFlowButtonProps) => {
  const start = useStartFlow(flowId);
  const [confirming, setConfirming] = useState(false);
  const request = () => {
    if (realMoney) {
      setConfirming(true);
      return;
    }
    start.mutate();
  };
  return (
    <div>
      {confirming ? (
        <RealMoneyStartConfirmation
          pending={start.isPending}
          onConfirm={() => start.mutate(undefined, { onSettled: () => setConfirming(false) })}
          onCancel={() => setConfirming(false)}
        />
      ) : (
        <button
          type="button"
          disabled={start.isPending}
          onClick={request}
          className={PRIMARY_COMMAND}
        >
          Avvia
        </button>
      )}
      <CommandRefusal refusal="Avvio rifiutato" error={start.error} />
    </div>
  );
};
