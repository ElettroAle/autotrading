/** A command of the API on a flow, as its path names it (R1.1.4-R1.1.6). */
export type FlowCommand = 'start' | 'pause' | 'resume' | 'stop' | 'archive';

/** A command of every day, offered on the page of the flow. */
export type OperatingCommand = Exclude<FlowCommand, 'archive'>;

// The only copy of the transitions of the domain (ADR 0132): a new status there needs a row here. The API stays the
// authority, so a command it refuses shows its reason even if this copy diverged.
const COMMANDS_BY_STATUS: Readonly<Record<string, readonly FlowCommand[]>> = {
  bozza: ['start', 'archive'],
  fermo: ['start', 'archive'],
  attivo: ['pause', 'stop'],
  'in pausa': ['resume', 'stop'],
  archiviato: [],
};

/** The commands the status of a flow admits, in the order the dashboard offers them. */
export const commandsAllowedIn = (status: string): readonly FlowCommand[] =>
  COMMANDS_BY_STATUS[status] ?? [];

/** The commands of every day the page of the flow offers: Archivia is in its settings (ADR
 * impostazioni-del-flusso-dall-ingranaggio). */
export const operatingCommandsIn = (status: string): readonly OperatingCommand[] =>
  commandsAllowedIn(status).filter((command): command is OperatingCommand => command !== 'archive');

/** Whether the settings of the flow offer Archivia: only a stopped flow or a draft is archived (R1.1.6). */
export const isArchivable = (status: string): boolean =>
  commandsAllowedIn(status).includes('archive');
