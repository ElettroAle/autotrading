/** A page a notification leads to, as the API describes it (ADR notifiche-nell-app-salvate-per-tenant). */
export type FakeInboxTarget = {
  readonly kind: 'flow' | 'open_position' | 'closed_position' | 'alert';
  readonly label: string;
  readonly flow_id: string | null;
  readonly asset: string | null;
  readonly closed_at: string | null;
  readonly alert_id: string | null;
};

/** A notification of the bell as the API keeps it (R6.2.1). */
export type FakeInboxNotification = {
  readonly id: string;
  readonly icon: string;
  readonly title: string;
  readonly text: string;
  readonly notified_at: string;
  read_at: string | null;
  readonly targets: readonly FakeInboxTarget[];
};

/** What the platform tells in a notification: the rest is the bell's. */
export type FakeNotice = {
  readonly icon?: string;
  readonly title: string;
  readonly text?: string;
  readonly targets?: readonly FakeInboxTarget[];
};

/** The notifications of a page, as the API gives them (ADR 0074). */
export const INBOX_PAGE_SIZE = 20;

const WARNING_ICON = '⚠️';

const notificationsOfTenants = new Map<string, FakeInboxNotification[]>();
const counter = { notified: 0 };

const storedOf = (tenantId: string): FakeInboxNotification[] => {
  const known = notificationsOfTenants.get(tenantId);
  if (known !== undefined) {
    return known;
  }
  const created: FakeInboxNotification[] = [];
  notificationsOfTenants.set(tenantId, created);
  return created;
};

// The fake keeps its own cursor, the place of the next notification: the dashboard only hands back what the API gave.
const startOf = (cursor: string | null): number => (cursor === null ? 0 : Number(cursor));

/** The page of the flow a notification of the flow leads to. */
export const flowTarget = (flowId: string): FakeInboxTarget => ({
  kind: 'flow',
  label: 'Apri flusso',
  flow_id: flowId,
  asset: null,
  closed_at: null,
  alert_id: null,
});

/** The detail of the alert the notification opened. */
export const alertTarget = (alertId: string): FakeInboxTarget => ({
  kind: 'alert',
  label: 'Apri avviso',
  flow_id: null,
  asset: null,
  closed_at: null,
  alert_id: alertId,
});

/**
 * The bell of every tenant behind the fake API, as the worker fills it and the API reads it (R6.2.1): each notification
 * the platform generates, whatever its channels.
 */
export const fakeInbox = {
  reset(): void {
    notificationsOfTenants.clear();
    counter.notified = 0;
  },

  /** Keeps a notification of the tenant generated at the instant, unread. */
  notify(tenantId: string, notice: FakeNotice, at: Date): FakeInboxNotification {
    counter.notified += 1;
    const notification: FakeInboxNotification = {
      id: `notification-${counter.notified}`,
      icon: notice.icon ?? WARNING_ICON,
      title: notice.title,
      text: notice.text ?? '',
      notified_at: at.toISOString(),
      read_at: null,
      targets: notice.targets ?? [],
    };
    storedOf(tenantId).push(notification);
    return notification;
  },

  /** Every notification of the tenant, newest first. */
  notificationsOf(tenantId: string): FakeInboxNotification[] {
    return storedOf(tenantId).toSorted((first, second) =>
      second.notified_at.localeCompare(first.notified_at),
    );
  },

  pageOf(tenantId: string, cursor: string | null) {
    const start = startOf(cursor);
    const all = this.notificationsOf(tenantId);
    const end = start + INBOX_PAGE_SIZE;
    return { items: all.slice(start, end), next: end < all.length ? String(end) : null };
  },

  unreadCount(tenantId: string): number {
    return storedOf(tenantId).filter((notification) => notification.read_at === null).length;
  },

  /** Reads a notification of the tenant: false when the tenant has none with the id. */
  markRead(tenantId: string, notificationId: string, at: Date): boolean {
    const notification = storedOf(tenantId).find((candidate) => candidate.id === notificationId);
    if (notification === undefined) {
      return false;
    }
    notification.read_at ??= at.toISOString();
    return true;
  },

  markAllRead(tenantId: string, at: Date): void {
    storedOf(tenantId).forEach((notification) => {
      notification.read_at ??= at.toISOString();
    });
  },
};
