import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

const sourceParameterSchema = z.object({
  key: z.string(),
  label: z.string(),
  default: z.number(),
  minimum: z.number(),
  maximum: z.number(),
  // Empty for a parameter that admits its whole range; otherwise only these values (ADR orizzonti-lunghi-del-forecast).
  choices: z.array(z.object({ value: z.number(), label: z.string() })),
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
  // An adapter that needs configuration says whether the tenant gave it and, when not, why it is not activatable;
  // none for an adapter that needs no configuration (R4.1.2).
  configured: z.boolean().nullable(),
  unavailable_reason: z.string().nullable(),
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
