/**
 * Said wherever the user looks at a flow whose openings are suspended for maximum loss: the threshold passed, as the API
 * gives it (R3.2.2, ADR perdita-massima-nella-dashboard).
 */
export const OpeningsSuspendedNotice = ({ reason }: { readonly reason: string }) => (
  <p role="status" className="rounded bg-amber-100 px-2 py-1 font-semibold text-amber-900">
    {`aperture sospese: ${reason}`}
  </p>
);
