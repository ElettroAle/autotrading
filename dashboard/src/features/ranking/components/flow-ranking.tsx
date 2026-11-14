import { Link } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { apiSearchOf, usePeriod, type Period } from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { MAX_COMPARED_FLOWS } from '@/utils/compared-flows';
import {
  formatAmount,
  formatPercent,
  formatRate,
  formatRoundedResult,
  formatUsd,
} from '@/utils/format-amount';

import { useFlowRanking, type FlowRankingRow } from '../api/get-flow-ranking';
import { useComparedFlows } from '../hooks/use-compared-flows';
import { useRankingSort } from '../hooks/use-ranking-sort';
import { sortRanking } from '../utils/sort-ranking';

const NOT_AVAILABLE = 'non disponibile';

const orNotAvailable = (text: string | null, format: (value: string) => string): string =>
  text === null ? NOT_AVAILABLE : format(text);

type Comparison = {
  readonly chosen: readonly string[];
  readonly toggle: (flowId: string) => void;
};

const CompareBox = ({ row, comparison }: { row: FlowRankingRow; comparison: Comparison }) => {
  const checked = comparison.chosen.includes(row.flow_id);
  return (
    <input
      type="checkbox"
      aria-label={`Confronta ${row.flow_name}`}
      checked={checked}
      disabled={!checked && comparison.chosen.length >= MAX_COMPARED_FLOWS}
      onChange={() => comparison.toggle(row.flow_id)}
    />
  );
};

// The values are the API's: the page formats them and sorts them, and computes nothing (ADR 0136).
const columnsFor = (comparison: Comparison): DataTableColumn<FlowRankingRow>[] => [
  { header: 'Confronta', cell: (row) => <CompareBox row={row} comparison={comparison} /> },
  {
    header: 'Flusso',
    sortKey: 'name',
    cell: (row) => (
      <Link
        to={paths.flow.getHref(row.flow_id)}
        className="font-medium text-blue-800 hover:underline"
      >
        {row.flow_name}
      </Link>
    ),
  },
  {
    header: 'Rendimento',
    sortKey: 'return',
    cell: (row) => orNotAvailable(row.return_percent, formatPercent),
  },
  { header: 'PnL', sortKey: 'pnl', cell: (row) => `${formatRoundedResult(row.pnl)} USDC` },
  {
    header: 'Commissioni',
    sortKey: 'fees',
    cell: (row) => `${formatAmount(row.total_fees)} USDC`,
  },
  {
    header: 'Win rate',
    sortKey: 'win-rate',
    cell: (row) => orNotAvailable(row.win_rate_percent, formatRate),
  },
  { header: 'Operazioni', sortKey: 'operations', cell: (row) => row.operations },
  {
    header: 'Drawdown massimo',
    sortKey: 'drawdown',
    cell: (row) => formatRate(row.max_drawdown_percent),
  },
  {
    header: 'Costo del modello IA',
    sortKey: 'model-cost',
    cell: (row) => `${formatUsd(row.model_cost_usd)} USD`,
  },
];

const CompareLink = ({ period, chosen }: { period: Period; chosen: readonly string[] }) => (
  <p className="mt-4">
    <Link
      to={paths.comparison.getHref(chosen, apiSearchOf(period))}
      className="text-blue-800 hover:underline"
    >
      Confronta le curve
    </Link>
  </p>
);

const RankingTable = ({ rows, period }: { rows: FlowRankingRow[]; period: Period }) => {
  const [sort, sortBy] = useRankingSort();
  const [chosen, toggle] = useComparedFlows();
  return (
    <>
      <p className="mb-2 text-sm text-slate-600">
        Scegli fino a {MAX_COMPARED_FLOWS} flussi per confrontarne le equity curve.
      </p>
      <DataTable
        label="Classifica dei flussi"
        columns={columnsFor({ chosen, toggle })}
        rows={sortRanking(rows, sort)}
        rowKey={(row) => row.flow_id}
        empty="Nessun flusso con cicli nel periodo."
        sort={sort}
        onSort={sortBy}
      />
      {chosen.length > 0 && <CompareLink period={period} chosen={chosen} />}
    </>
  );
};

/** The ranking of the flows over the period chosen on the page, sortable by any column (R2.4.2). */
export const FlowRanking = () => {
  const [period] = usePeriod();
  const ranking = useFlowRanking(period);
  if (ranking.isPending && ranking.fetchStatus === 'idle') {
    return (
      <p className="text-slate-500">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  if (ranking.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (ranking.data === undefined) {
    return <ErrorMessage error={ranking.error} />;
  }
  return <RankingTable rows={ranking.data} period={period} />;
};
