import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { reconciliationAlarmSchema } from './get-account-reconciliation';

/** The alarms of reconciliation of an account, open and confirmed, the most recent first as the API lists them. */
export const useReconciliationAlarms = (accountId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('accounts', accountId, 'reconciliation', 'alarms'),
    queryFn: async () =>
      readData(
        await api.GET('/accounts/{account_id}/reconciliation/alarms', {
          params: { path: { account_id: accountId } },
        }),
        z.array(reconciliationAlarmSchema),
      ),
  });
};
