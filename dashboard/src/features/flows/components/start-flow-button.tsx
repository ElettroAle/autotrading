import { useState } from 'react';

import { RealMoneyStartConfirmation } from '@/components/ui/network-notice';

import { useStartFlow } from '../api/start-flow';

import { CommandRefusal } from './command-refusal';

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
          className="rounded bg-blue-700 px-3 py-1 text-white hover:bg-blue-800"
        >
          Avvia
        </button>
      )}
      <CommandRefusal refusal="Avvio rifiutato" error={start.error} />
    </div>
  );
};
