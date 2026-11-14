import { useStartFlow } from '../api/start-flow';

import { CommandRefusal } from './command-refusal';

export const StartFlowButton = ({ flowId }: { flowId: string }) => {
  const start = useStartFlow(flowId);
  return (
    <div>
      <button
        type="button"
        disabled={start.isPending}
        onClick={() => start.mutate()}
        className="rounded bg-blue-700 px-3 py-1 text-white hover:bg-blue-800"
      >
        Avvia
      </button>
      <CommandRefusal refusal="Avvio rifiutato" error={start.error} />
    </div>
  );
};
