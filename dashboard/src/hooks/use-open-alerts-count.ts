import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const alertsSummarySchema = z.object({ open_count: z.number() });

/**
 * How many alerts of the user are open, for the entry of the menu of every page: page data, reread with the page
 * (R2.1.2, ADR pagina-avvisi-nella-dashboard). Under the key of the alerts, so a command on an alert reads it again.
 */
export const useOpenAlertsCount = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('alerts', 'summary'),
    queryFn: async () => readData(await api.GET('/alerts/summary'), alertsSummarySchema),
    select: (summary) => summary.open_count,
  });
};
