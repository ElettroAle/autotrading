import { useId } from 'react';

import { Card } from '@/components/ui/card';
import { ErrorMessage } from '@/components/ui/error-message';
import { FlowMemoryTable } from '@/components/ui/flow-memory-table';

import { useFlowMemory } from '../api/get-flow-memory';

/**
 * The memory of the flow on its page, only with the memory on: for every asset, what the agent will receive at the next
 * cycle (R5.3.4, ADR memoria-del-flusso-dalle-decisioni-operative-precedenti).
 */
export const FlowMemory = ({ flowId }: { flowId: string }) => {
  const titleId = useId();
  const memory = useFlowMemory(flowId);
  if (memory.isPending || memory.data?.active === false) {
    return null;
  }
  return (
    <Card as="section" aria-labelledby={titleId} className="mt-4">
      <h3 id={titleId} className="text-lg font-semibold">
        Memoria
      </h3>
      <p className="mb-2 text-sm text-slate-600">
        ciò che l&apos;agente riceverà al prossimo ciclo
      </p>
      {/* A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119). */}
      {memory.data === undefined ? (
        <ErrorMessage error={memory.error} />
      ) : (
        <FlowMemoryTable memory={memory.data.assets} />
      )}
    </Card>
  );
};
