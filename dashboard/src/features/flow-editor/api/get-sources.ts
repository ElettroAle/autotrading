import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const sourceParameterSchema = z.object({
  key: z.string(),
  label: z.string(),
  default: z.number(),
  minimum: z.number(),
  maximum: z.number(),
});

export type SourceParameter = z.infer<typeof sourceParameterSchema>;

// An adapter of a source as it declares itself: no configuration field means none is needed (R4.1.1).
const sourceAdapterSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.array(sourceParameterSchema),
  configuration_fields: z.array(
    z.object({ name: z.string(), label: z.string(), secret: z.boolean() }),
  ),
  offers_history: z.boolean(),
});

export type SourceAdapter = z.infer<typeof sourceAdapterSchema>;

const sourceSchema = z.object({
  name: z.string(),
  description: z.string(),
  per_asset: z.boolean(),
  parameters: z.array(sourceParameterSchema),
  adapters: z.array(sourceAdapterSchema),
});

export type Source = z.infer<typeof sourceSchema>;

/** The sources of data the platform offers, each with the adapters that offer it (R1.3.1, R4.1.1). */
export const useSources = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['sources'],
    queryFn: async () => readData(await api.GET('/sources'), z.array(sourceSchema)),
  });
};
