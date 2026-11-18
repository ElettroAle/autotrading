import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient, type ApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const freeCapitalSchema = z.object({
  amount: z.string(),
  currency: z.string(),
  flows_value: z.string(),
  flows_result: z.string(),
});

type FreeCapital = z.infer<typeof freeCapitalSchema>;

// One reading of the free capital gives both its amount and the value of the flows, so they are of the same instant.
const freeCapitalQuery = (api: ApiClient, accountId: string) => ({
  ...pageDataQuery('accounts', accountId, 'free-capital'),
  queryFn: async () =>
    readData(
      await api.GET('/accounts/{account_id}/free-capital', {
        params: { path: { account_id: accountId } },
      }),
      freeCapitalSchema,
    ),
});

/**
 * The capital of one account still free for new flows, with the value and the result of its flows, as the API computes
 * them (R1.1.7, ADR scomposizione-del-saldo-nel-riquadro-del-conto).
 */
export const useFreeCapital = (accountId: string) =>
  useQuery(freeCapitalQuery(useApiClient(), accountId));

const flowsValueOf = (capital: FreeCapital) => ({
  amount: capital.flows_value,
  currency: capital.currency,
});

/** The value of the flows of one account, as an amount of the same reading of its free capital. */
export const useFlowsValue = (accountId: string) =>
  useQuery({ ...freeCapitalQuery(useApiClient(), accountId), select: flowsValueOf });
