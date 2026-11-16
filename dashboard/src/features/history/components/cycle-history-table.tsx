import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { paths } from '@/config/paths';
import { formatInstant } from '@/utils/format-instant';

import type { HistoryCycle } from '../api/get-cycle-history';

const UNKNOWN = '—';

const outcomeOf = (cycle: HistoryCycle): string =>
  cycle.failure === null ? cycle.outcome : `${cycle.outcome} nel passo «${cycle.failure.step}»`;

const COLUMNS: DataTableColumn<HistoryCycle>[] = [
  { header: 'Istante', cell: (cycle) => formatInstant(cycle.planned_at) },
  { header: 'Flusso', cell: (cycle) => cycle.flow },
  { header: 'Versione', cell: (cycle) => cycle.version ?? UNKNOWN },
  { header: 'Esito', cell: outcomeOf },
];

/** The cycles found, each row leading to the page of its cycle (ADR 0129, R6.4.4). */
export const CycleHistoryTable = ({ cycles }: { cycles: readonly HistoryCycle[] }) => (
  <DataTable
    label="Cicli"
    columns={COLUMNS}
    rows={cycles}
    rowKey={(cycle) => `${cycle.flow_id}/${cycle.planned_at}`}
    rowHref={(cycle) => paths.cycle.getHref(cycle.flow_id, cycle.planned_at)}
    empty="Nessun ciclo trovato."
  />
);
