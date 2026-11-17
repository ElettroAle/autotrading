import { DataTable, type DataTableColumn } from '@/components/ui/data-table';

import type { EmergencyClosing, FlowEmergencyOutcome } from '../api/close-in-emergency';

const notClosedOf = (outcome: FlowEmergencyOutcome): string => {
  const refused = outcome.left_open.map((position) => `${position.asset}: ${position.reason}`);
  const failed = outcome.failure === null ? [] : [`chiusura non riuscita: ${outcome.failure}`];
  return [...refused, ...failed].join('; ');
};

const COLUMNS: DataTableColumn<FlowEmergencyOutcome>[] = [
  { header: 'Flusso', cell: (outcome) => outcome.flow_name },
  { header: 'Posizioni chiuse', cell: (outcome) => outcome.closed.join(', ') },
  { header: 'Non chiuse', cell: notClosedOf },
  { header: 'Note', cell: (outcome) => outcome.remark ?? '' },
];

const fullyClosed = (closing: EmergencyClosing): boolean =>
  closing.flows.every((outcome) => outcome.left_open.length === 0 && outcome.failure === null);

/** What the emergency closing did to each flow: closed, not closed with the reason, or nothing to close (R3.2.3). */
export const EmergencyClosingOutcome = ({ closing }: { readonly closing: EmergencyClosing }) => (
  <div className="space-y-2">
    {fullyClosed(closing) ? (
      <p role="status">Chiusura di emergenza eseguita: i flussi sono in pausa.</p>
    ) : (
      <p role="alert" className="text-red-700">
        Chiusura di emergenza incompleta: alcune posizioni non sono state chiuse. I flussi sono in
        pausa.
      </p>
    )}
    <DataTable
      label="Esito della chiusura di emergenza"
      columns={COLUMNS}
      rows={closing.flows}
      rowKey={(outcome) => outcome.flow_id}
      empty="Nessun flusso da chiudere."
    />
  </div>
);
