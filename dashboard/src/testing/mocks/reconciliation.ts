/** The last comparison of the balance of an account, as the API answers it (R3.3.1). */
export type FakeBalanceComparison = {
  readonly compared_at: string;
  readonly expected_balance: string;
  readonly read_balance: string;
  readonly deviation_percent: string;
};

/** An alarm of reconciliation of an account, open until the user confirms it (R3.3.1). */
export type FakeReconciliationAlarm = {
  readonly expected_balance: string;
  readonly read_balance: string;
  readonly deviation_percent: string;
  readonly opened_at: string;
  confirmed_at: string | null;
};

type FakeReconciliation = {
  thresholdPercent: string;
  lastComparison: FakeBalanceComparison | null;
  readonly alarms: FakeReconciliationAlarm[];
};

const DEFAULT_THRESHOLD = '1';
const LOWEST_THRESHOLD = 0.1;
const HIGHEST_THRESHOLD = 100;
const DEVIATION_DECIMALS = 4;

/** The reason the API gives a threshold out of its range, with the same words. */
export const THRESHOLD_OUT_OF_RANGE = 'la soglia di scostamento va da 0,1 a 100';

// The API writes amounts without trailing zeros (ADR 0018).
const amountText = (amount: number): string => String(Number(amount.toFixed(DEVIATION_DECIMALS)));

// How far the read balance is from the expected one, either way, in percent of the expected balance.
const deviationOf = (expected: number, read: number): string =>
  amountText(
    expected === 0 ? (read === 0 ? 0 : 100) : (Math.abs(read - expected) / expected) * 100,
  );

const comparisonOf = (expected: number, read: number, at: Date): FakeBalanceComparison => ({
  compared_at: at.toISOString(),
  expected_balance: amountText(expected),
  read_balance: amountText(read),
  deviation_percent: deviationOf(expected, read),
});

const reconciliations = new Map<string, FakeReconciliation>();

const reconciliationOf = (accountId: string): FakeReconciliation => {
  const known = reconciliations.get(accountId);
  if (known !== undefined) {
    return known;
  }
  const created: FakeReconciliation = {
    thresholdPercent: DEFAULT_THRESHOLD,
    lastComparison: null,
    alarms: [],
  };
  reconciliations.set(accountId, created);
  return created;
};

const openAlarmOf = (accountId: string): FakeReconciliationAlarm | undefined =>
  reconciliationOf(accountId).alarms.find((alarm) => alarm.confirmed_at === null);

/**
 * The reconciliation of the balance of the accounts behind the fake API: threshold, last comparison and alarms of each
 * account, as the worker would leave them (R3.3.1). Scenarios and unit tests prepare it.
 */
export const fakeReconciliation = {
  reset(): void {
    reconciliations.clear();
  },

  /** The last reconciliation of the account compared the balances at the instant. */
  compare(accountId: string, expected: number, read: number, at: Date): void {
    reconciliationOf(accountId).lastComparison = comparisonOf(expected, read, at);
  },

  /** The balance read went beyond the threshold at the instant: the comparison opens an alarm. */
  openAlarm(accountId: string, expected: number, read: number, at: Date): void {
    const comparison = comparisonOf(expected, read, at);
    const reconciliation = reconciliationOf(accountId);
    reconciliation.lastComparison = comparison;
    reconciliation.alarms.push({
      expected_balance: comparison.expected_balance,
      read_balance: comparison.read_balance,
      deviation_percent: comparison.deviation_percent,
      opened_at: comparison.compared_at,
      confirmed_at: null,
    });
  },

  /** An alarm opened and confirmed in the past. */
  closedAlarm(accountId: string, openedAt: Date, confirmedAt: Date): void {
    this.openAlarm(accountId, 1000, 980, openedAt);
    this.confirm(accountId, confirmedAt);
  },

  /** Closes the open alarm of the account at the instant; false when the account has none. */
  confirm(accountId: string, at: Date): boolean {
    const alarm = openAlarmOf(accountId);
    if (alarm === undefined) {
      return false;
    }
    alarm.confirmed_at = at.toISOString();
    return true;
  },

  /** Sets the threshold of the account, as text; false when the API refuses it. */
  setThreshold(accountId: string, percent: string): boolean {
    const value = Number(percent);
    if (Number.isNaN(value) || value < LOWEST_THRESHOLD || value > HIGHEST_THRESHOLD) {
      return false;
    }
    reconciliationOf(accountId).thresholdPercent = amountText(value);
    return true;
  },

  thresholdOf(accountId: string): string {
    return reconciliationOf(accountId).thresholdPercent;
  },

  /** The reconciliation of the account, as the API answers it. */
  statusOf(accountId: string) {
    const { thresholdPercent, lastComparison } = reconciliationOf(accountId);
    const alarm = openAlarmOf(accountId) ?? null;
    return {
      aligned: alarm === null,
      threshold_percent: thresholdPercent,
      last_comparison: lastComparison,
      open_alarm: alarm,
    };
  },

  /** The alarms of the account, open and confirmed, the most recent first. */
  alarmsOf(accountId: string): FakeReconciliationAlarm[] {
    return reconciliationOf(accountId).alarms.toSorted((first, second) =>
      second.opened_at.localeCompare(first.opened_at),
    );
  },

  /** Why the openings of the flows of the account are suspended, with the words of the API; null when they are not. */
  openingsSuspendedOf(accountId: string, accountName: string): string | null {
    return openAlarmOf(accountId) === undefined
      ? null
      : `allarme di riconciliazione sul conto ${accountName}`;
  },
};
