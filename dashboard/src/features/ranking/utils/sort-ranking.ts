import type { DataTableSort } from '@/components/ui/data-table';

import type { FlowRankingRow } from '../api/get-flow-ranking';

type Value = (row: FlowRankingRow) => string | number | null;

const NUMERIC_VALUES = {
  return: (row) => row.return_percent,
  pnl: (row) => row.pnl,
  fees: (row) => row.total_fees,
  'win-rate': (row) => row.win_rate_percent,
  operations: (row) => row.operations,
  drawdown: (row) => row.max_drawdown_percent,
  'model-cost': (row) => row.model_cost_usd,
} satisfies Record<string, Value>;

export type RankingSortKey = 'name' | keyof typeof NUMERIC_VALUES;

/** The order of the API, from the highest return (ADR 0135). */
export const DEFAULT_RANKING_SORT = { key: 'return', direction: 'descending' } as const;

export const isRankingSortKey = (key: string | null): key is RankingSortKey =>
  key === 'name' || (key !== null && Object.hasOwn(NUMERIC_VALUES, key));

const byName = (one: FlowRankingRow, other: FlowRankingRow): number =>
  one.flow_name.localeCompare(other.flow_name, 'it');

// The decimal text of the API compares as a number; what is not available stays at the bottom in either direction.
const byNumber =
  (value: Value, sign: number) =>
  (one: FlowRankingRow, other: FlowRankingRow): number => {
    const first = value(one);
    const second = value(other);
    if (first === null || second === null) {
      return Number(first === null) - Number(second === null);
    }
    return sign * (Number(first) - Number(second));
  };

/** The rows in the order the user chose, computed on the values received and never recomputed (ADR 0136). */
export const sortRanking = (
  rows: readonly FlowRankingRow[],
  sort: DataTableSort,
): FlowRankingRow[] => {
  const sign = sort.direction === 'ascending' ? 1 : -1;
  if (!isRankingSortKey(sort.key) || sort.key === 'name') {
    return rows.toSorted((one, other) => sign * byName(one, other));
  }
  return rows.toSorted(byNumber(NUMERIC_VALUES[sort.key], sign));
};
