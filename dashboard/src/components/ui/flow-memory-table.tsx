import type { AssetMemory } from '@/types/flow-memory';
import { formatPrice, formatSignedAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import { ActionLabel } from './action-label';
import { DataTable, type DataTableColumn } from './data-table';
import { DirectionLabel } from './direction-label';

type Decision = AssetMemory['entries'][number];

const NOTHING = '—';

const pnlText = (outcome: NonNullable<Decision['outcome']>): string =>
  `${formatSignedAmount(outcome.pnl)} ${outcome.realized ? 'realizzato' : 'non realizzato'}`;

const outcomeText = (outcome: NonNullable<Decision['outcome']>): string =>
  outcome.course == null ? pnlText(outcome) : `${outcome.course}, ${pnlText(outcome)}`;

const COLUMNS: readonly DataTableColumn<Decision>[] = [
  { header: 'Istante', cell: (decision) => formatInstant(decision.planned_at) },
  {
    header: 'Azione',
    cell: (decision) => (
      <span className="inline-flex gap-2">
        <ActionLabel value={decision.action} />
        {decision.direction !== null && <DirectionLabel value={decision.direction} />}
      </span>
    ),
  },
  {
    header: 'Prezzo',
    cell: (decision) => (decision.price === null ? NOTHING : formatPrice(decision.price)),
  },
  {
    header: 'Esito',
    cell: (decision) => (decision.outcome === null ? NOTHING : outcomeText(decision.outcome)),
  },
  { header: 'Motivo', cell: (decision) => decision.motive },
  { header: 'Invalidazione', cell: (decision) => decision.invalidation ?? NOTHING },
];

// Summary lines as the API writes them, as the agent receives them; nothing without lines.
const SummaryLines = ({
  label,
  lines,
}: {
  readonly label: string;
  readonly lines: readonly string[];
}) =>
  lines.length === 0 ? null : (
    <div className="text-sm">
      <p className="text-slate-600">{label}</p>
      <ul aria-label={label} className="list-inside list-disc">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );

/**
 * The memory of a flow, one table per asset with its previous decisions from the most recent, with motive, invalidation
 * and the course of the position: on the page of the flow what the agent will receive, in the detail of a cycle what it
 * received (R5.3.4, R5.3.5, ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni). Before the table,
 * the summary lines of the asset and those of the other assets, with the text of the API (R5.3.7, ADR
 * opzioni-della-memoria-nella-dashboard).
 */
export const FlowMemoryTable = ({ memory }: { readonly memory: readonly AssetMemory[] }) => (
  <div className="space-y-3">
    {memory.map(({ asset, summary, other_assets: otherAssets, entries }) => (
      <section key={asset} aria-label={asset} className="space-y-1">
        <h4 className="font-semibold">{asset}</h4>
        <SummaryLines label={`Riepilogo di ${asset}`} lines={summary} />
        <SummaryLines label="Altri asset del flusso" lines={otherAssets} />
        <DataTable
          label={`Memoria di ${asset}`}
          columns={COLUMNS}
          rows={entries}
          rowKey={(decision) => decision.planned_at}
          empty="Nessuna decisione precedente."
        />
      </section>
    ))}
  </div>
);
