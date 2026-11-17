import { useState } from 'react';
import { Link } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { CommandRefusal } from '@/components/ui/command-refusal';
import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { RealMoneyStartConfirmation } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';

import { useStartFlow } from '../api/start-flow';
import { listed } from '../utils/listed';

type StartFlowButtonProps = {
  readonly flowId: string;
  readonly realMoney: boolean;
  /** What the draft lacks to start, as the API declares it (ADR mancanze-della-bozza-dichiarate-dall-api). */
  readonly missing: readonly string[];
};

// While the draft lacks something Avvia stays disabled, with what is missing and the way to the configuration (Bug 560).
const MissingBeforeStart = ({
  flowId,
  missing,
}: {
  flowId: string;
  missing: readonly string[];
}) => (
  <div role="group" aria-label="Avvio della bozza" className="flex flex-wrap items-center gap-2">
    <p>Per avviarla manca: {listed(missing)}</p>
    <Link to={paths.editFlow.getHref(flowId)} className={SECONDARY_COMMAND}>
      Configura
    </Link>
  </div>
);

/** Starts a draft that lacks nothing; on an account that trades real money only once the user confirms it (Bug 277). */
export const StartFlowButton = ({ flowId, realMoney, missing }: StartFlowButtonProps) => {
  const start = useStartFlow(flowId);
  const [confirming, setConfirming] = useState(false);
  const request = () => {
    if (realMoney) {
      setConfirming(true);
      return;
    }
    start.mutate();
  };
  const incomplete = missing.length > 0;
  return (
    <div className="space-y-2">
      {confirming ? (
        <RealMoneyStartConfirmation
          pending={start.isPending}
          onConfirm={() => start.mutate(undefined, { onSettled: () => setConfirming(false) })}
          onCancel={() => setConfirming(false)}
        />
      ) : (
        <CommandButton
          tone="go"
          icon="play"
          disabled={start.isPending || incomplete}
          onClick={request}
        >
          Avvia
        </CommandButton>
      )}
      {incomplete && <MissingBeforeStart flowId={flowId} missing={missing} />}
      <CommandRefusal refusal="Avvio rifiutato" error={start.error} />
    </div>
  );
};
