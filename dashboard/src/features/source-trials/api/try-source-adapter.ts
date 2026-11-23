import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

// What the adapter answered: a source that fails is the outcome of the trial, not a refusal (R6.3.1).
const trialSchema = z.object({
  outcome: z.enum(['succeeded', 'failed']),
  values: z.array(z.object({ reference_at: z.string(), values: z.record(z.string(), z.string()) })),
  data_at: z.string().nullable(),
  response_milliseconds: z.number(),
  reason: z.string().nullable(),
  permanent: z.boolean(),
});

export type SourceTrial = z.infer<typeof trialSchema>;

export type SourceTrialRequest = {
  readonly source: string;
  readonly adapter: string;
  /** None for a source of the whole market. */
  readonly asset: string | null;
  readonly parameters: Readonly<Record<string, number | number[]>>;
};

/** Asks the platform to read the adapter now, as a cycle does, without recording anything (R6.3.1). */
export const useTrySourceAdapter = () => {
  const api = useApiClient();
  return useMutation({
    mutationFn: async ({ source, adapter, asset, parameters }: SourceTrialRequest) =>
      readData(
        await api.POST('/sources/{name}/adapters/{adapter}/trials', {
          params: { path: { name: source, adapter } },
          body: { asset, parameters: { ...parameters } },
        }),
        trialSchema,
      ),
  });
};
