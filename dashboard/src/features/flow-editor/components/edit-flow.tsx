import { useMemo, useState } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { isDraft, useFlow, type Flow } from '../api/get-flow';
import { useModifyFlow } from '../api/save-flow';
import { changesOf, formValuesOf, type FlowFormValues } from '../utils/flow-form';

import { FlowForm } from './flow-form';
import { WithCatalogs } from './with-catalogs';

const savedMessageOf = (flow: Flow, modified: Flow): string => {
  if (modified.version !== flow.version) {
    return `Modifiche salvate: versione ${modified.version}`;
  }
  return modified.name === flow.name ? 'Nessuna modifica da salvare' : 'Modifiche salvate';
};

const FlowEditor = ({ flow }: { flow: Flow }) => {
  const modifyFlow = useModifyFlow(flow);
  const [saved, setSaved] = useState<string>();
  const values = useMemo(() => formValuesOf(flow), [flow]);

  // Every change is a new version, in force from the next cycle (R1.1.3); a new name alone is not (ADR
  // nome-del-flusso-modificabile).
  const save = async (submitted: FlowFormValues) => {
    setSaved(undefined);
    const modified = await modifyFlow.mutateAsync(changesOf(flow, submitted));
    setSaved(savedMessageOf(flow, modified));
  };

  return (
    <div className="space-y-3">
      <h2 className="text-xl font-semibold">{flow.name}</h2>
      <p className="text-slate-600">Versione in vigore: {flow.version}</p>
      <p role="status" className="text-green-800">
        {saved}
      </p>
      <WithCatalogs>
        {(catalogs) => (
          <FlowForm
            {...catalogs}
            values={values}
            accountChosen={isDraft(flow)}
            submitLabel="Salva le modifiche"
            onSave={save}
          />
        )}
      </WithCatalogs>
    </div>
  );
};

/** The configuration of a flow of the tenant, changed from the dashboard (R2.3.3). */
export const EditFlow = ({ flowId }: { flowId: string }) => {
  const flow = useFlow(flowId);
  if (flow.isPending) {
    return <Loading />;
  }
  if (flow.isError) {
    return <ErrorMessage error={flow.error} />;
  }
  if (flow.data === undefined) {
    return <p>Flusso non trovato.</p>;
  }
  return <FlowEditor flow={flow.data} />;
};
