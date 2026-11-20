import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const parameterSchema = z.object({
  key: z.string(),
  label: z.string(),
  default: z.number(),
  minimum: z.number(),
  maximum: z.number(),
  // Empty for a parameter that admits its whole range; otherwise only these values (ADR orizzonti-lunghi-del-forecast).
  choices: z.array(z.object({ value: z.number(), label: z.string() })),
});

export type TrialParameter = z.infer<typeof parameterSchema>;

// An adapter with every parameter a trial may set: those of the source and its own (R4.1.1).
const adapterSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.array(parameterSchema),
});

export type TrialAdapter = z.infer<typeof adapterSchema>;

const sourceSchema = z.object({
  name: z.string(),
  description: z.string(),
  per_asset: z.boolean(),
  adapters: z.array(adapterSchema),
});

export type TrialSource = z.infer<typeof sourceSchema>;

/** The sources of the catalog, each with the adapters a trial reads (R1.3.1, R6.3.1, ADR 0131). */
export const useTrialSources = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['source-trials', 'sources'],
    queryFn: async () => readData(await api.GET('/sources'), z.array(sourceSchema)),
  });
};
