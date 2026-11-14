import type { FlowRankingRow } from '../api/get-flow-ranking';

import { DEFAULT_RANKING_SORT, isRankingSortKey, sortRanking } from './sort-ranking';

const row = (name: string, values: Partial<FlowRankingRow> = {}): FlowRankingRow => ({
  flow_id: `flow-${name}`,
  flow_name: name,
  return_percent: '0.00',
  max_drawdown_percent: '0.00',
  pnl: '0',
  total_fees: '0',
  win_rate_percent: null,
  operations: 0,
  model_cost_usd: '0',
  model_calls_without_cost: 0,
  ...values,
});

const names = (rows: FlowRankingRow[]) => rows.map((ranked) => ranked.flow_name);

describe('sortRanking', () => {
  const alfa = row('alfa', { return_percent: '20.00', max_drawdown_percent: '10.00', pnl: '9' });
  const beta = row('beta', { return_percent: '5.00', max_drawdown_percent: '0.00', pnl: '10.5' });
  const gamma = row('gamma', { return_percent: null, max_drawdown_percent: '2.00', pnl: '-3' });

  it('goes from the highest return by default', () => {
    expect(names(sortRanking([beta, gamma, alfa], DEFAULT_RANKING_SORT))).toEqual([
      'alfa',
      'beta',
      'gamma',
    ]);
  });

  it('compares the decimal values of the API as numbers', () => {
    expect(
      names(sortRanking([alfa, beta, gamma], { key: 'pnl', direction: 'descending' })),
    ).toEqual(['beta', 'alfa', 'gamma']);
  });

  it('sorts in ascending order', () => {
    expect(
      names(sortRanking([alfa, gamma, beta], { key: 'drawdown', direction: 'ascending' })),
    ).toEqual(['beta', 'gamma', 'alfa']);
  });

  it('keeps what is not available at the bottom in either direction', () => {
    expect(
      names(sortRanking([gamma, alfa, beta], { key: 'return', direction: 'ascending' })),
    ).toEqual(['beta', 'alfa', 'gamma']);
  });

  it('sorts the names in Italian', () => {
    expect(
      names(sortRanking([beta, gamma, alfa], { key: 'name', direction: 'ascending' })),
    ).toEqual(['alfa', 'beta', 'gamma']);
  });

  it('sorts every numeric column', () => {
    const many = row('molte', {
      win_rate_percent: '60.00',
      operations: 5,
      total_fees: '3',
      model_cost_usd: '2',
    });
    const few = row('poche', {
      win_rate_percent: '40.00',
      operations: 2,
      total_fees: '1',
      model_cost_usd: '1',
    });
    for (const key of ['win-rate', 'operations', 'fees', 'model-cost'] as const) {
      expect(names(sortRanking([few, many], { key, direction: 'descending' }))).toEqual([
        'molte',
        'poche',
      ]);
    }
  });

  it('does not change the rows it receives', () => {
    const rows = [beta, alfa];

    sortRanking(rows, DEFAULT_RANKING_SORT);

    expect(names(rows)).toEqual(['beta', 'alfa']);
  });
});

describe('isRankingSortKey', () => {
  it('knows the columns of the ranking only', () => {
    expect(isRankingSortKey('drawdown')).toBe(true);
    expect(isRankingSortKey('colore')).toBe(false);
    expect(isRankingSortKey(null)).toBe(false);
  });
});
