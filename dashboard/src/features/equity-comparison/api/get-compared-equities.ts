import { useQueries } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, type Period } from '@/components/ui/period-selector/use-period';
import { useApiClient } from '@/lib/api-client';

// The API computes the change of each point from the first point of the period (ADR 0137); the chart needs numbers.
const changesSchema = z
  .object({
    points: z.array(z.object({ planned_at: z.string(), change_percent: z.string().nullable() })),
  })
  .transform((equity) =>
    equity.points.map((point) => ({
      plannedAt: point.planned_at,
      changePercent: point.change_percent === null ? null : Number(point.change_percent),
    })),
  );

export type ComparedEquity = z.infer<typeof changesSchema>;

const equityPath = (flowId: string, period: Period): string =>
  `/flows/${encodeURIComponent(flowId)}/equity?${apiSearchOf(period)}`;

/** The equity curve of each compared flow in the period, one query per flow on the same endpoint (ADR 0137). */
export const useComparedEquities = (flowIds: readonly string[], period: Period) => {
  const api = useApiClient();
  return useQueries({
    queries: flowIds.map((flowId) => {
      const path = equityPath(flowId, period);
      return { queryKey: ['compared-equity', path], queryFn: () => api.get(path, changesSchema) };
    }),
  });
};
