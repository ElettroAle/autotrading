// The look of the commands, the same on every page: large enough to touch on a phone, the main command filled and a
// command that destroys in red (ADR viste-e-comandi-della-pagina-del-flusso); the commands of the status of a flow in
// a colour of their own, with an icon beside the text (ADR icone-con-lucide-react-e-comandi-condivisi).
const COMMAND = 'inline-flex min-h-11 items-center gap-2 rounded px-3 disabled:opacity-50';

/** The command a page leads to, as «Nuovo flusso». */
export const PRIMARY_COMMAND = `${COMMAND} bg-blue-700 text-white hover:bg-blue-800`;

/** Any other command, as «Importa» and «Duplica». */
export const SECONDARY_COMMAND = `${COMMAND} border border-slate-300 bg-white hover:bg-slate-100`;

/** A command whose effect cannot be undone, as «Archivia». */
export const DESTRUCTIVE_COMMAND = `${COMMAND} border border-red-300 bg-white text-red-800 hover:bg-red-50`;

/** A command that sets a flow running, as «Avvia» and «Riprendi». */
export const GO_COMMAND = `${COMMAND} bg-green-700 text-white hover:bg-green-800`;

/** A command that holds a flow, as «Pausa»: dark text, as amber is too light for white to read on it. */
export const HOLD_COMMAND = `${COMMAND} bg-amber-600 text-slate-950 hover:bg-amber-500`;

/** A command that stops a flow, or confirms an operation that cannot be undone, as «Stop». */
export const STOP_COMMAND = `${COMMAND} bg-red-700 text-white hover:bg-red-800`;
