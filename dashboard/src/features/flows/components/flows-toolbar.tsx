import { useId, useState } from 'react';
import { Link } from 'react-router';

import { PRIMARY_COMMAND, SECONDARY_COMMAND } from '@/components/ui/commands';
import { paths } from '@/config/paths';

import { ImportStrategyForm } from './import-strategy-form';

/** The actions on the flows: a new flow, and the import of a strategy opened on request (ADR 0161). */
export const FlowsToolbar = () => {
  const [importOpen, setImportOpen] = useState(false);
  const importId = useId();
  return (
    <div className="mb-4">
      <div className="flex flex-wrap gap-2">
        <Link to={paths.newFlow.getHref()} className={PRIMARY_COMMAND}>
          Nuovo flusso
        </Link>
        <button
          type="button"
          aria-expanded={importOpen}
          aria-controls={importId}
          onClick={() => setImportOpen((open) => !open)}
          className={SECONDARY_COMMAND}
        >
          Importa
        </button>
      </div>
      <div id={importId}>{importOpen && <ImportStrategyForm />}</div>
    </div>
  );
};
