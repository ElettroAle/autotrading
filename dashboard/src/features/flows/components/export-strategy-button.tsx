import { CommandRefusal } from '@/components/ui/command-refusal';
import { SECONDARY_COMMAND } from '@/components/ui/commands';

import { useExportFlowStrategy } from '../api/export-flow-strategy';

/** Saves the strategy of the flow in a file, to keep it or to use it again (R2.5.2, ADR 0141). */
export const ExportStrategyButton = ({ flowId }: { flowId: string }) => {
  const exportStrategy = useExportFlowStrategy();
  return (
    <div>
      <button
        type="button"
        disabled={exportStrategy.isPending}
        onClick={() => exportStrategy.mutate(flowId)}
        className={SECONDARY_COMMAND}
      >
        Esporta
      </button>
      <CommandRefusal refusal="Esportazione rifiutata" error={exportStrategy.error} />
    </div>
  );
};
