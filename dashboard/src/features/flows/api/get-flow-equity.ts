import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiSearchOf, type Period } from '@/components/ui/period-selector/use-period';
import { useApiClient } from '@/lib/api-client';

// Amounts travel as text, so no precision is lost on the way (ADR 0018); the chart needs numbers.
const equitySchema = z
  .object({
    initial_capital: z.string().nullable(),
    points: z.array(z.object({ planned_at: z.string(), equity: z.string() })),
  })
  .transform((equity) => ({
    initialCapital: equity.initial_capital === null ? null : Number(equity.initial_capital),
    points: equity.points.map((point) => ({
      plannedAt: point.planned_at,
      equity: Number(point.equity),
    })),
  }));

export type FlowEquity = z.infer<typeof equitySchema>;

/** The path of the curve in the period, with the same periods as the statistics (ADR 0122). */
export const equityPath = (flowId: string, period: Period): string =>
  `/flows/${encodeURIComponent(flowId)}/equity?${apiSearchOf(period)}`;

/** The equity curve of a flow of the tenant in the period: a point for each cycle (R2.2.3). */
export const useFlowEquity = (flowId: string, period: Period) => {
  const api = useApiClient();
  const path = equityPath(flowId, period);
  return useQuery({
    queryKey: ['flow-equity', path],
    queryFn: () => api.get(path, equitySchema),
    placeholderData: keepPreviousData,
  });
};
