import { useState } from 'react';
import { useNavigate } from 'react-router';

import { paths } from '@/config/paths';

import { useCreateFlow } from '../api/save-flow';
import { creationRequestOf, emptyFormValues, type FlowFormValues } from '../utils/flow-form';

import { FlowForm } from './flow-form';
import { WithCatalogs } from './with-catalogs';

/** A new flow from the dashboard: once the API saves it, the user finds it among the flows (R2.3.3). */
export const CreateFlow = () => {
  const navigate = useNavigate();
  const createFlow = useCreateFlow();
  const [values] = useState(emptyFormValues);

  const create = async (submitted: FlowFormValues) => {
    await createFlow.mutateAsync(creationRequestOf(submitted));
    await navigate(paths.home.getHref());
  };

  return (
    <WithCatalogs>
      {(catalogs) => (
        <FlowForm {...catalogs} values={values} submitLabel="Crea il flusso" onSave={create} />
      )}
    </WithCatalogs>
  );
};
