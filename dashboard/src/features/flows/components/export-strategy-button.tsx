import { useExportFlowStrategy } from '../api/export-flow-strategy';

import { CommandRefusal } from './command-refusal';

/** Saves the strategy of the flow in a file, to keep it or to use it again (R2.5.2, ADR 0141). */
export const ExportStrategyButton = ({ flowId }: { flowId: string }) => {
  const exportStrategy = useExportFlowStrategy();
  return (
    <div>
      <button
        type="button"
        disabled={exportStrategy.isPending}
        onClick={() => exportStrategy.mutate(flowId)}
        className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
      >
        Esporta
      </button>
      <CommandRefusal refusal="Esportazione rifiutata" error={exportStrategy.error} />
    </div>
  );
};
