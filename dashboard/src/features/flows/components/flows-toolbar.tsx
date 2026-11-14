import { useId, useState } from 'react';
import { Link } from 'react-router';

import { paths } from '@/config/paths';

import { ImportStrategyForm } from './import-strategy-form';

/** The actions on the flows: a new flow, and the import of a strategy opened on request (ADR 0159). */
export const FlowsToolbar = () => {
  const [importOpen, setImportOpen] = useState(false);
  const importId = useId();
  return (
    <div className="mb-4">
      <div className="flex flex-wrap gap-2">
        <Link
          to={paths.newFlow.getHref()}
          className="inline-flex min-h-11 items-center rounded bg-blue-700 px-3 text-white"
        >
          Nuovo flusso
        </Link>
        <button
          type="button"
          aria-expanded={importOpen}
          aria-controls={importId}
          onClick={() => setImportOpen((open) => !open)}
          className="inline-flex min-h-11 items-center rounded border border-slate-300 bg-white px-3 hover:bg-slate-100"
        >
          Importa
        </button>
      </div>
      <div id={importId}>{importOpen && <ImportStrategyForm />}</div>
    </div>
  );
};
