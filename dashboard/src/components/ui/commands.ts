// The look of the commands, the same on every page: large enough to touch on a phone, the main command filled and a
// command that destroys in red (ADR viste-e-comandi-della-pagina-del-flusso).
const COMMAND = 'inline-flex min-h-11 items-center rounded px-3 disabled:opacity-50';

/** The command a page leads to, as «Nuovo flusso» and «Avvia». */
export const PRIMARY_COMMAND = `${COMMAND} bg-blue-700 text-white hover:bg-blue-800`;

/** Any other command, as «Importa» and «Duplica». */
export const SECONDARY_COMMAND = `${COMMAND} border border-slate-300 bg-white hover:bg-slate-100`;

/** A command whose effect cannot be undone, as «Archivia». */
export const DESTRUCTIVE_COMMAND = `${COMMAND} border border-red-300 bg-white text-red-800 hover:bg-red-50`;
