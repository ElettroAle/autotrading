import { fakeReconciliation } from './reconciliation';

export type FakeAlertKind =
  'reconciliation_alarm' | 'flow_paused' | 'unattributable_position' | 'unattributable_fill';

export type FakeAlertResource = {
  readonly kind: 'account' | 'flow' | 'key';
  readonly id: string;
  readonly name: string;
};

export type FakeAlertValue = { readonly label: string; readonly value: string };

/** An alert as the API keeps it (R6.2.3): its kind, the resource it is about, the values read when it opened. */
export type FakeAlert = {
  readonly id: string;
  readonly kind: FakeAlertKind;
  readonly resource: FakeAlertResource;
  readonly values: readonly FakeAlertValue[];
  readonly opened_at: string;
  resolved_at: string | null;
};

/** What the dashboard asks of the list of the alerts, as the parameters of the API. */
export type FakeAlertsQuery = {
  readonly state: string | null;
  readonly severity: string | null;
  readonly resourceKind: string | null;
  readonly resourceId: string | null;
  readonly since: string | null;
  readonly until: string | null;
  readonly cursor: string | null;
};

/** An account of the tenant, whose alarms of reconciliation are alerts. */
export type FakeAlertAccount = {
  readonly id: string;
  readonly name: string;
  readonly currency: string;
};

type Traits = {
  readonly title: string;
  readonly severity: 'critical' | 'warning';
  readonly commands: readonly ('confirm_reconciliation' | 'resume_flow' | 'resolve')[];
};

// The same traits of the kinds of the domain (ADR avvisi-nel-contesto-delle-notifiche).
const TRAITS: Readonly<Record<FakeAlertKind, Traits>> = {
  reconciliation_alarm: {
    title: 'Allarme di riconciliazione',
    severity: 'critical',
    commands: ['confirm_reconciliation'],
  },
  flow_paused: {
    title: 'Flusso in pausa automatica',
    severity: 'critical',
    commands: ['resume_flow'],
  },
  unattributable_position: {
    title: 'Posizione su un asset di nessun flusso',
    severity: 'warning',
    commands: [],
  },
  unattributable_fill: {
    title: 'Esecuzione senza identificativo della piattaforma',
    severity: 'warning',
    commands: ['resolve'],
  },
};

/** The alerts of a page, as the API gives them (ADR 0074). */
export const ALERT_PAGE_SIZE = 50;

/** The reason the API gives when the user resolves by hand an alert that resolves on its own. */
export const NOT_RESOLVABLE_BY_HAND = "l'avviso si risolve da solo quando la sua causa sparisce";

const alertsOfTenants = new Map<string, FakeAlert[]>();
const counter = { opened: 0 };

const storedOf = (tenantId: string): FakeAlert[] => {
  const known = alertsOfTenants.get(tenantId);
  if (known !== undefined) {
    return known;
  }
  const created: FakeAlert[] = [];
  alertsOfTenants.set(tenantId, created);
  return created;
};

// The alarms of reconciliation are kept by the reconciliation of the account: as on the API, the alert opens with the
// alarm and the confirmation of the balance resolves both.
const alarmAlertsOf = (account: FakeAlertAccount): FakeAlert[] =>
  fakeReconciliation.alarmsOf(account.id).map((alarm) => ({
    id: `alarm-${account.id}-${alarm.opened_at}`,
    kind: 'reconciliation_alarm',
    resource: { kind: 'account', id: account.id, name: account.name },
    values: [
      { label: 'Saldo letto', value: `${alarm.read_balance} ${account.currency}` },
      { label: 'Saldo atteso', value: `${alarm.expected_balance} ${account.currency}` },
    ],
    opened_at: alarm.opened_at,
    resolved_at: alarm.confirmed_at,
  }));

const stateOf = (alert: FakeAlert): 'open' | 'resolved' =>
  alert.resolved_at === null ? 'open' : 'resolved';

const admits = (query: FakeAlertsQuery, alert: FakeAlert): boolean => {
  const state = query.state ?? 'open';
  const at = Date.parse(alert.opened_at);
  return (
    (state === 'all' || stateOf(alert) === state) &&
    (query.severity === null || TRAITS[alert.kind].severity === query.severity) &&
    (query.resourceKind === null || alert.resource.kind === query.resourceKind) &&
    (query.resourceId === null || alert.resource.id === query.resourceId) &&
    (query.since === null || at >= Date.parse(query.since)) &&
    (query.until === null || at < Date.parse(query.until))
  );
};

// The fake keeps its own cursor, the place of the next alert: the dashboard only hands back what the API gave.
const startOf = (cursor: string | null): number => (cursor === null ? 0 : Number(cursor));

const answerOf = (alert: FakeAlert) => {
  const { title, severity } = TRAITS[alert.kind];
  return {
    id: alert.id,
    kind: alert.kind,
    title,
    severity,
    state: stateOf(alert),
    resource: alert.resource,
    opened_at: alert.opened_at,
    resolved_at: alert.resolved_at,
  };
};

const isOpenPauseOf =
  (flowId: string) =>
  (alert: FakeAlert): boolean =>
    alert.kind === 'flow_paused' && alert.resource.id === flowId && alert.resolved_at === null;

/**
 * The alerts of the tenants behind the fake API, as the worker and the API would leave them (R6.2.3): the alarms of
 * reconciliation come from the reconciliation of the accounts, the others are opened by scenarios and unit tests.
 */
export const fakeAlerts = {
  reset(): void {
    alertsOfTenants.clear();
    counter.opened = 0;
  },

  /** Opens an alert of the tenant at the instant, with the values read. */
  open(
    tenantId: string,
    kind: Exclude<FakeAlertKind, 'reconciliation_alarm'>,
    resource: FakeAlertResource,
    values: readonly FakeAlertValue[],
    at: Date,
  ): FakeAlert {
    counter.opened += 1;
    const alert: FakeAlert = {
      id: `alert-${counter.opened}`,
      kind,
      resource,
      values,
      opened_at: at.toISOString(),
      resolved_at: null,
    };
    storedOf(tenantId).push(alert);
    return alert;
  },

  /** The open alert of the pause of the flow is resolved: the flow resumed, stopped or was archived. */
  resolveFlowPause(flowId: string, at: Date): void {
    alertsOfTenants.forEach((alerts) =>
      alerts.filter(isOpenPauseOf(flowId)).forEach((alert) => {
        alert.resolved_at = at.toISOString();
      }),
    );
  },

  /** Every alert of the tenant, newest first. */
  alertsOf(tenantId: string, accounts: readonly FakeAlertAccount[]): FakeAlert[] {
    return [...storedOf(tenantId), ...accounts.flatMap(alarmAlertsOf)].toSorted((first, second) =>
      second.opened_at.localeCompare(first.opened_at),
    );
  },

  /** A page of the alerts of the tenant the query admits, with how many it admits in all. */
  pageOf(tenantId: string, accounts: readonly FakeAlertAccount[], query: FakeAlertsQuery) {
    const admitted = this.alertsOf(tenantId, accounts).filter((alert) => admits(query, alert));
    const start = startOf(query.cursor);
    const end = start + ALERT_PAGE_SIZE;
    return {
      items: admitted.slice(start, end).map(answerOf),
      next: end < admitted.length ? String(end) : null,
      count: admitted.length,
    };
  },

  /** The alert with its values and the commands that resolve it while it is open; undefined when the tenant has none. */
  detailOf(tenantId: string, accounts: readonly FakeAlertAccount[], alertId: string) {
    const alert = this.alertsOf(tenantId, accounts).find((candidate) => candidate.id === alertId);
    if (alert === undefined) {
      return undefined;
    }
    const commands = alert.resolved_at === null ? TRAITS[alert.kind].commands : [];
    return { ...answerOf(alert), values: alert.values, commands };
  },

  /** Resolves an alert of the tenant by hand: false when its kind resolves on its own. */
  resolveByHand(tenantId: string, alertId: string, at: Date): boolean {
    const alert = storedOf(tenantId).find((candidate) => candidate.id === alertId);
    if (alert === undefined || !TRAITS[alert.kind].commands.includes('resolve')) {
      return false;
    }
    alert.resolved_at ??= at.toISOString();
    return true;
  },
};
