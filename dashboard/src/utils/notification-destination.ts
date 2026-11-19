import { paths } from '@/config/paths';

/** A page a notification leads to, as the API describes it (ADR notifiche-nell-app-salvate-per-tenant). */
export type NotificationTarget = {
  readonly kind: 'flow' | 'open_position' | 'closed_position' | 'alert';
  readonly flow_id: string | null;
  readonly asset: string | null;
  readonly closed_at: string | null;
  readonly alert_id: string | null;
};

type Destination = (target: NotificationTarget) => string | undefined;

const DESTINATIONS: Readonly<Record<NotificationTarget['kind'], Destination>> = {
  flow: ({ flow_id }) => (flow_id === null ? undefined : paths.flow.getHref(flow_id)),
  open_position: ({ flow_id, asset }) =>
    flow_id === null || asset === null ? undefined : paths.flowPositions.getHref(flow_id, asset),
  closed_position: ({ flow_id, asset, closed_at }) =>
    flow_id === null || asset === null || closed_at === null
      ? undefined
      : paths.flowClosedPositions.getHref(flow_id, 1, { asset, closedAt: closed_at }),
  alert: ({ alert_id }) => (alert_id === null ? undefined : paths.alert.getHref(alert_id)),
};

/**
 * The page of the dashboard the target of a notification leads to, by its kind (ADR
 * campanello-delle-notifiche-nella-dashboard); none without a target, or without what finds its page.
 */
export const destinationOf = (target: NotificationTarget | undefined): string | undefined =>
  target === undefined ? undefined : DESTINATIONS[target.kind](target);
