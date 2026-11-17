import { useId, useState } from 'react';
import { Link } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { PRIMARY_COMMAND } from '@/components/ui/commands';
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
        <CommandButton
          tone="secondary"
          aria-expanded={importOpen}
          aria-controls={importId}
          onClick={() => setImportOpen((open) => !open)}
        >
          Importa
        </CommandButton>
      </div>
      <div id={importId}>{importOpen && <ImportStrategyForm />}</div>
    </div>
  );
};
