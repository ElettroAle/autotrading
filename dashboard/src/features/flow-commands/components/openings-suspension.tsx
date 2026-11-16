import { useState } from 'react';

import { PRIMARY_COMMAND } from '@/components/ui/commands';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { OpeningsSuspendedNotice } from '@/components/ui/openings-notice';

import { useFlowOpenings } from '../api/get-flow-openings';
import { useResumeFlowOpenings } from '../api/resume-flow-openings';

/**
 * The openings of the flow suspended for maximum loss, with why, and the command that resumes them once the user
 * confirms (R3.2.2, ADR perdita-massima-nella-dashboard). Nothing while the flow may open.
 */
export const OpeningsSuspension = ({ flowId }: { readonly flowId: string }) => {
  const [confirming, setConfirming] = useState(false);
  const openings = useFlowOpenings(flowId);
  const resume = useResumeFlowOpenings(flowId);
  // A failed rereading keeps the suspension already read on the page: the warning is the page's (ADR 0119).
  if (openings.data === undefined) {
    return openings.isError ? <ErrorMessage error={openings.error} /> : null;
  }
  const { suspension } = openings.data;
  if (suspension === null) {
    return null;
  }
  return (
    <section aria-label="Aperture sospese" className="mt-3 space-y-2">
      <OpeningsSuspendedNotice reason={suspension.reason} />
      {confirming ? (
        <ConfirmationDialog
          title="Conferma della ripresa delle aperture"
          confirmLabel="Conferma la ripresa"
          onConfirm={() => resume.mutate(undefined, { onSettled: () => setConfirming(false) })}
          onCancel={() => setConfirming(false)}
          pending={resume.isPending}
        >
          <p>Il flusso tornerà ad aprire posizioni e il picco ripartirà dal suo valore di ora.</p>
        </ConfirmationDialog>
      ) : (
        <button type="button" onClick={() => setConfirming(true)} className={PRIMARY_COMMAND}>
          Riprendi le aperture
        </button>
      )}
      {resume.isError && <ErrorMessage error={resume.error} prefix="Ripresa non riuscita" />}
    </section>
  );
};
