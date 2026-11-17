import { useState } from 'react';

import { PRIMARY_COMMAND } from '@/components/ui/commands';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { OpeningsSuspendedNotice } from '@/components/ui/openings-notice';

import { useOpeningsSuspension } from '../api/get-openings-suspension';
import { useResumeFlowOpenings } from '../api/resume-flow-openings';

/**
 * The openings of the flow suspended, with why, whatever the cause; the command that resumes them, once the user
 * confirms, only when the API says the user may: after a maximum loss, not while an alarm of reconciliation is open
 * (R3.2.2, R3.3.2, ADR perdita-massima-nella-dashboard). Nothing while the flow may open, or while its state cannot be
 * read: the tabs show their own errors.
 */
export const OpeningsSuspension = ({ flowId }: { readonly flowId: string }) => {
  const [confirming, setConfirming] = useState(false);
  const suspension = useOpeningsSuspension(flowId).data;
  const resume = useResumeFlowOpenings(flowId);
  // A failed rereading keeps the suspension already read on the page (ADR 0119).
  if (suspension === undefined || suspension === null) {
    return null;
  }
  return (
    <section aria-label="Aperture sospese" className="mt-3 space-y-2">
      <OpeningsSuspendedNotice reason={suspension.reason} />
      {!suspension.resumable ? null : confirming ? (
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
