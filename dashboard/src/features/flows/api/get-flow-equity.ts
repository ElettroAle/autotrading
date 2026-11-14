import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

// Amounts travel as text, so no precision is lost on the way (ADR 0018); the chart needs numbers.
const equitySchema = z
  .object({
    initial_capital: z.string(),
    points: z.array(z.object({ planned_at: z.string(), equity: z.string() })),
  })
  .transform((equity) => ({
    initialCapital: Number(equity.initial_capital),
    points: equity.points.map((point) => ({
      plannedAt: point.planned_at,
      equity: Number(point.equity),
    })),
  }));

export type FlowEquity = z.infer<typeof equitySchema>;

/** The period of the curve: the whole life of the flow, the last days, or a range from a start to an end. */
export type EquityPeriod =
  | { readonly kind: 'lifetime' | '7d' | '30d' }
  | { readonly kind: 'range'; readonly start: Date; readonly end: Date };

export const equityPath = (flowId: string, period: EquityPeriod): string => {
  const query = new URLSearchParams({ period: period.kind });
  if (period.kind === 'range') {
    query.set('from', period.start.toISOString());
    query.set('to', period.end.toISOString());
  }
  return `/flows/${encodeURIComponent(flowId)}/equity?${query.toString()}`;
};

/** The equity curve of a flow of the tenant in the period: a point for each cycle (R2.2.3). */
export const useFlowEquity = (flowId: string, period: EquityPeriod) => {
  const api = useApiClient();
  const path = equityPath(flowId, period);
  return useQuery({
    queryKey: ['flow-equity', path],
    queryFn: () => api.get(path, equitySchema),
    placeholderData: keepPreviousData,
  });
};
