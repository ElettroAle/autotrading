import { useInfiniteQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const unattributableSchema = z.object({
  detected_at: z.string(),
  kind: z.enum(['posizione', 'esecuzione', 'variazione del saldo']),
  asset: z.string().nullable(),
  amount: z.string(),
});

export type Unattributable = z.infer<typeof unattributableSchema>;

export type UnattributableKind = Unattributable['kind'];

const unattributablePageSchema = z.object({
  items: z.array(unattributableSchema),
  next: z.string().nullable(),
  count: z.number(),
  net_change: z.string(),
});

export type UnattributablePage = z.infer<typeof unattributablePageSchema>;

/** What the record of an account is asked for: a kind, and the instants of the period, absent where it does not limit. */
export type UnattributableQuery = {
  readonly kind?: string;
  readonly since?: string;
  readonly until?: string;
};

/**
 * The record of what no flow explains on an account, newest first, in the pages of the API: the next page starts after
 * the last case of the previous one; count and net of the changes cover the whole filter (ADR
 * movimenti-non-spiegati-nel-riquadro-del-conto).
 */
export const useUnattributable = (accountId: string, query: UnattributableQuery) => {
  const api = useApiClient();
  return useInfiniteQuery({
    ...pageDataQuery('accounts', accountId, 'reconciliation', 'unattributable', query),
    queryFn: async ({ pageParam }) =>
      readData(
        await api.GET('/accounts/{account_id}/reconciliation/unattributable', {
          params: {
            path: { account_id: accountId },
            query: {
              kind: query.kind as UnattributableKind | undefined,
              since: query.since,
              until: query.until,
              cursor: pageParam ?? undefined,
            },
          },
        }),
        unattributablePageSchema,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
  });
};
