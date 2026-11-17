import { CommandButton } from '@/components/ui/command-button';

import { useExportFlowStrategy } from '../api/export-flow-strategy';

import { CommandRefusal } from './command-refusal';

/** Saves the strategy of the flow in a file, to keep it or to use it again (R2.5.2, ADR 0141). */
export const ExportStrategyButton = ({ flowId }: { flowId: string }) => {
  const exportStrategy = useExportFlowStrategy();
  return (
    <div>
      <CommandButton
        tone="secondary"
        disabled={exportStrategy.isPending}
        onClick={() => exportStrategy.mutate(flowId)}
      >
        Esporta
      </CommandButton>
      <CommandRefusal refusal="Esportazione rifiutata" error={exportStrategy.error} />
    </div>
  );
};
