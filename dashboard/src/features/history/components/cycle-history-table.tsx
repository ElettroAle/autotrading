import { Link } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { paths } from '@/config/paths';
import { formatInstant } from '@/utils/format-instant';

import type { HistoryCycle } from '../api/get-cycle-history';

const UNKNOWN = '—';

const outcomeOf = (cycle: HistoryCycle): string =>
  cycle.failure === null ? cycle.outcome : `${cycle.outcome} nel passo «${cycle.failure.step}»`;

const COLUMNS: DataTableColumn<HistoryCycle>[] = [
  {
    header: 'Istante',
    cell: (cycle) => (
      <Link
        to={paths.cycle.getHref(cycle.flow_id, cycle.planned_at)}
        className="font-medium text-blue-800 hover:underline"
      >
        {formatInstant(cycle.planned_at)}
      </Link>
    ),
  },
  { header: 'Flusso', cell: (cycle) => cycle.flow },
  { header: 'Versione', cell: (cycle) => cycle.version ?? UNKNOWN },
  { header: 'Esito', cell: outcomeOf },
];

/** The cycles found, each leading to its own page (ADR 0129). */
export const CycleHistoryTable = ({ cycles }: { cycles: readonly HistoryCycle[] }) => (
  <DataTable
    label="Cicli"
    columns={COLUMNS}
    rows={cycles}
    rowKey={(cycle) => `${cycle.flow_id}/${cycle.planned_at}`}
    empty="Nessun ciclo trovato."
  />
);
