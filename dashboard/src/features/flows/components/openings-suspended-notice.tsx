import { useOpeningsSuspension } from '../api/get-openings-suspension';

/**
 * Said on the page of a flow whose openings are suspended, with the reason the API gives: an alarm of reconciliation
 * on its account (R3.3.2). A state that cannot be read says nothing here: the tabs show their own errors.
 */
export const OpeningsSuspendedNotice = ({ flowId }: { readonly flowId: string }) => {
  const reason = useOpeningsSuspension(flowId).data;
  if (reason === undefined || reason === null) {
    return null;
  }
  return (
    <p role="note" className="rounded bg-red-100 px-2 py-1 font-semibold text-red-900">
      {`aperture sospese: ${reason}`}
    </p>
  );
};
