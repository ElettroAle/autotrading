import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { ALERTS_QUERY_KEY, alertSchema } from './get-alerts';

const alertDetailSchema = alertSchema.extend({
  values: z.array(z.object({ label: z.string(), value: z.string() })),
  commands: z.array(z.enum(['confirm_reconciliation', 'resume_flow', 'resolve'])),
});

export type AlertDetail = z.infer<typeof alertDetailSchema>;

export type AlertCommand = AlertDetail['commands'][number];

/** An alert with the values read when it opened and the commands the API admits now (R6.2.3). */
export const useAlert = (alertId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...ALERTS_QUERY_KEY, 'detail', alertId),
    queryFn: async () =>
      readData(
        await api.GET('/alerts/{alert_id}', { params: { path: { alert_id: alertId } } }),
        alertDetailSchema,
      ),
  });
};
