import { contains, windowOf } from './flow-statistics';

/**
 * The histories of R2.5.1 as the API serves them: each row keeps what the filters read of it (flow, account, instant,
 * assets, configuration version) beside the body the API answers. Unit tests and scenarios build them here.
 */
export type FakeHistoryRow<T> = {
  readonly flowId: string | null;
  readonly accountId: string;
  readonly at: string;
  readonly key: string;
  readonly assets: readonly string[];
  readonly version: number | null;
  readonly body: T;
};

export type FakeHistoryCycle = {
  readonly flow_id: string;
  readonly flow: string;
  readonly version: number | null;
  readonly planned_at: string;
  readonly started_at: string | null;
  readonly outcome: string;
  readonly failure: {
    readonly step: string;
    readonly error_type: string;
    readonly message: string;
  } | null;
  readonly decisions: null;
};

export type FakeHistoryPosition = {
  readonly id: string;
  readonly flow_id: string;
  readonly flow: string;
  readonly asset: string;
  readonly side: string;
  readonly leverage: number;
  readonly margin: string;
  readonly open_price: string;
  readonly close_price: string;
  readonly opened_at: string;
  readonly closed_at: string;
  readonly duration_seconds: number;
  readonly pnl: string;
  readonly pnl_percent_of_margin: string;
  readonly fees: string;
  readonly reason: string;
  readonly opening_cycle: string | null;
  readonly closing_cycle: string | null;
};

export type FakeExecution = {
  readonly executed_at: string;
  readonly price: string;
  readonly size: string;
  readonly fee: string;
};

export type FakeHistoryOrder = {
  readonly id: string;
  readonly created_at: string;
  readonly account_id: string;
  readonly account: string;
  readonly flow_id: string | null;
  readonly flow: string | null;
  readonly asset: string;
  readonly direction: string;
  readonly closing: boolean;
  readonly leverage: number;
  readonly requested_size: string;
  readonly status: string;
  readonly origin: string;
  readonly executions: FakeExecution[];
};

/** The histories of one tenant. */
export type FakeRecords = {
  readonly cycles: FakeHistoryRow<FakeHistoryCycle>[];
  readonly closedPositions: FakeHistoryRow<FakeHistoryPosition>[];
  readonly orders: FakeHistoryRow<FakeHistoryOrder>[];
};

export const emptyRecords = (): FakeRecords => ({ cycles: [], closedPositions: [], orders: [] });

/** Where a row of a history belongs: its flow, of a configuration version, on its account. */
export type FakeOwner = {
  readonly flowId: string;
  readonly flow: string;
  readonly accountId: string;
  readonly account: string;
  readonly version: number;
};

const PAGE_SIZE = 50;
const SECOND = 1000;
const HOUR = 3600 * SECOND;

/** The instant as the API writes it: UTC, to the second. */
const apiInstant = (instant: Date): string => instant.toISOString().replace('.000Z', 'Z');

export const aHistoryCycle = (
  owner: FakeOwner,
  plannedAt: Date,
  assets: readonly string[],
): FakeHistoryRow<FakeHistoryCycle> => {
  const at = apiInstant(plannedAt);
  return {
    flowId: owner.flowId,
    accountId: owner.accountId,
    at,
    key: owner.flowId,
    assets,
    version: owner.version,
    body: {
      flow_id: owner.flowId,
      flow: owner.flow,
      version: owner.version,
      planned_at: at,
      started_at: at,
      outcome: 'concluso',
      failure: null,
      decisions: null,
    },
  };
};

export const aHistoryPosition = (
  owner: FakeOwner,
  asset: string,
  closedAt: Date,
): FakeHistoryRow<FakeHistoryPosition> => {
  const at = apiInstant(closedAt);
  const id = `position-${owner.flowId}-${asset}-${at}`;
  return {
    flowId: owner.flowId,
    accountId: owner.accountId,
    at,
    key: id,
    assets: [asset],
    version: owner.version,
    body: {
      id,
      flow_id: owner.flowId,
      flow: owner.flow,
      asset,
      side: 'long',
      leverage: 2,
      margin: '100',
      open_price: '3000',
      close_price: '3150',
      opened_at: apiInstant(new Date(closedAt.getTime() - 2 * HOUR)),
      closed_at: at,
      duration_seconds: 7200,
      pnl: '10',
      pnl_percent_of_margin: '10',
      fees: '0.42',
      reason: "decisione dell'agente",
      opening_cycle: null,
      closing_cycle: null,
    },
  };
};

export const anExecution = (
  executedAt: Date,
  price: string,
  size: string,
  fee: string,
): FakeExecution => ({
  executed_at: apiInstant(executedAt),
  price,
  size,
  fee,
});

export const aHistoryOrder = (
  owner: FakeOwner,
  asset: string,
  createdAt: Date,
  executions: FakeExecution[],
): FakeHistoryRow<FakeHistoryOrder> => {
  const at = apiInstant(createdAt);
  const id = `order-${owner.flowId}-${asset}-${at}`;
  return {
    flowId: owner.flowId,
    accountId: owner.accountId,
    at,
    key: id,
    assets: [asset],
    version: owner.version,
    body: {
      id,
      created_at: at,
      account_id: owner.accountId,
      account: owner.account,
      flow_id: owner.flowId,
      flow: owner.flow,
      asset,
      direction: 'long',
      closing: false,
      leverage: 2,
      requested_size: '0.02',
      status: 'eseguito',
      origin: 'flusso',
      executions,
    },
  };
};

/** The answer of the API to a search it refuses, with the reason it gives (R2.5.1). */
export class InvalidSearch extends Error {}

const cursorOf = (row: FakeHistoryRow<unknown>): string => btoa(`${row.at}|${row.key}`);

const newerFirst = (one: FakeHistoryRow<unknown>, other: FakeHistoryRow<unknown>): number =>
  Date.parse(other.at) - Date.parse(one.at) || other.key.localeCompare(one.key);

/** One page of the history the search admits, newest first, and the cursor of the next page if there is one. */
export const historyPage = <T>(
  rows: readonly FakeHistoryRow<T>[],
  search: URLSearchParams,
  now = Date.now(),
): { readonly found: T[]; readonly next: string | null } => {
  const flow = search.get('flow_id');
  const account = search.get('account_id');
  const asset = search.get('asset');
  const version = search.get('version');
  if (version !== null && flow === null) {
    throw new InvalidSearch('la versione richiede un flusso');
  }
  const window = windowOf(search, now);
  const sorted = rows
    .filter(
      (row) =>
        (flow === null || row.flowId === flow) &&
        (account === null || row.accountId === account) &&
        (asset === null || row.assets.includes(asset)) &&
        (version === null || row.version === Number(version)) &&
        contains(window, new Date(row.at)),
    )
    .sort(newerFirst);
  const after = search.get('after');
  const start = after === null ? 0 : sorted.findIndex((row) => cursorOf(row) === after) + 1;
  const page = sorted.slice(start, start + PAGE_SIZE);
  const last = page.at(-1);
  const more = sorted.length > start + PAGE_SIZE;
  return {
    found: page.map((row) => row.body),
    next: more && last !== undefined ? cursorOf(last) : null,
  };
};
