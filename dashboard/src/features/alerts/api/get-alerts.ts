import { useInfiniteQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

/** The key of every read of the alerts: a command on an alert invalidates them all. */
export const ALERTS_QUERY_KEY = ['alerts'] as const;

export const alertSchema = z.object({
  id: z.string(),
  kind: z.enum([
    'reconciliation_alarm',
    'flow_paused',
    'unattributable_position',
    'unattributable_fill',
  ]),
  title: z.string(),
  severity: z.enum(['critical', 'warning']),
  state: z.enum(['open', 'resolved']),
  resource: z.object({
    kind: z.enum(['account', 'flow', 'key']),
    id: z.string(),
    name: z.string(),
  }),
  opened_at: z.string(),
  resolved_at: z.string().nullable(),
});

export type Alert = z.infer<typeof alertSchema>;

export type AlertSeverity = Alert['severity'];

const alertPageSchema = z.object({
  items: z.array(alertSchema),
  next: z.string().nullable(),
  count: z.number(),
});

export type AlertPage = z.infer<typeof alertPageSchema>;

/** What the list of the alerts is asked for: the values of its filters, absent where they do not narrow. */
export type AlertsQuery = {
  readonly state: 'open' | 'resolved' | 'all';
  readonly severity?: string;
  readonly resourceKind?: string;
  readonly resourceId?: string;
  readonly since?: string;
};

/** The alerts of the user the filters admit, newest first, in the pages of the API (R6.2.3, ADR 0074). */
export const useAlerts = (query: AlertsQuery) => {
  const api = useApiClient();
  return useInfiniteQuery({
    ...pageDataQuery(...ALERTS_QUERY_KEY, 'list', query),
    queryFn: async ({ pageParam }) =>
      readData(
        await api.GET('/alerts', {
          params: {
            query: {
              state: query.state,
              severity: query.severity as AlertSeverity | undefined,
              resource_kind: query.resourceKind as Alert['resource']['kind'] | undefined,
              resource_id: query.resourceId,
              since: query.since,
              cursor: pageParam ?? undefined,
            },
          },
        }),
        alertPageSchema,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
  });
};
