import { CollapsibleSection } from '@/components/ui/collapsible-section';
import { ErrorMessage } from '@/components/ui/error-message';
import { FlowMemoryTable } from '@/components/ui/flow-memory-table';

import { useFlowMemory } from '../api/get-flow-memory';

export const FLOW_MEMORY_TITLE = "Memoria dell'agente";

/**
 * The memory of the flow in the tab Decisioni, only with the memory on: a detail read on demand, so a section closed
 * until the user opens it, with what the agent will receive at the next cycle for every asset (R5.3.4, ADR
 * memoria-del-flusso-dalle-decisioni-operative-precedenti).
 */
export const FlowMemory = ({ flowId }: { flowId: string }) => {
  const memory = useFlowMemory(flowId);
  if (memory.isPending || memory.data?.active === false) {
    return null;
  }
  return (
    <div className="mb-4">
      <CollapsibleSection title={FLOW_MEMORY_TITLE} open={false}>
        <p className="text-sm text-slate-600">ciò che l&apos;agente riceverà al prossimo ciclo</p>
        {/* A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119). */}
        {memory.data === undefined ? (
          <ErrorMessage error={memory.error} />
        ) : (
          <FlowMemoryTable memory={memory.data.assets} />
        )}
      </CollapsibleSection>
    </div>
  );
};
