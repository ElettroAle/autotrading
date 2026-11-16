import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import type { ListDays } from '@/components/ui/period-selector/use-period';
import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

const changesPageSchema = z.object({
  has_next: z.boolean(),
  currency: z.string(),
  changes: z.array(z.object({ changed_at: z.string(), reason: z.string(), amount: z.string() })),
});

/** A change of the capital as the equity curve marks it: when, why and how much money moved. */
export type CapitalChangeMark = {
  readonly changedAt: string;
  readonly reason: string;
  readonly amount: string;
  readonly currency: string;
};

/**
 * The changes of the capital of the flow in the days of the period, every page of the history, to mark them on the
 * equity curve (ADR rendimento-composto-tra-le-variazioni-di-capitale).
 */
export const useCapitalChangeMarks = (flowId: string, days: ListDays) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery('flows', flowId, 'capital-change-marks', days),
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const marks: CapitalChangeMark[] = [];
      for (let page = 1; ; page += 1) {
        const read = readData(
          await api.GET('/flows/{flow_id}/capital-changes', {
            params: { path: { flow_id: flowId }, query: { page, ...days } },
          }),
          changesPageSchema,
        );
        marks.push(
          ...read.changes.map((change) => ({
            changedAt: change.changed_at,
            reason: change.reason,
            amount: change.amount,
            currency: read.currency,
          })),
        );
        if (!read.has_next) {
          return marks;
        }
      }
    },
  });
};
