import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, isComplete, type Period } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const accuracySchema = z.object({
  forecasts: z.array(
    z.object({
      asset: z.string(),
      horizon_minutes: z.number(),
      mean_absolute_error: z.string().nullable(),
      mean_percent_error: z.string().nullable(),
      evaluated: z.number(),
      unevaluable: z.number(),
    }),
  ),
});

export type ForecastAccuracy = z.infer<typeof accuracySchema>['forecasts'][number];

/**
 * The error of the forecasts of a flow over a period, by asset and horizon, as the API measures it (ADR
 * errore-medio-della-previsione-nell-api); a range waits for both its days.
 */
export const useForecastAccuracy = (flowId: string, period: Period) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('forecast-accuracy', flowId, period),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}/forecast-accuracy', {
          params: { path: { flow_id: flowId } },
          querySerializer: () => apiSearchOf(period),
        }),
        accuracySchema,
      ),
    enabled: isComplete(period),
  });
};
