import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

// A range has minimum and maximum, a choice its values; the default is always there (R1.4.2), and so is the description
// the platform gives it, the text of its info button (R5.5.7, ADR descrizioni-dei-parametri-di-fonti-e-modelli).
const modelParameterSchema = z.object({
  key: z.string(),
  label: z.string(),
  default: z.string(),
  description: z.string(),
  minimum: z.string().nullish(),
  maximum: z.string().nullish(),
  whole: z.boolean().nullish(),
  choices: z.array(z.string()).nullish(),
});

export type ModelParameter = z.infer<typeof modelParameterSchema>;

const modelSchema = z.object({
  name: z.string(),
  provider: z.string(),
  parameters: z.array(modelParameterSchema),
});

export type Model = z.infer<typeof modelSchema>;

const providerSchema = z.object({ name: z.string(), key_registered: z.boolean() });

/** A provider of models, with whether the user registered its key (R1.4.1). */
export type Provider = z.infer<typeof providerSchema>;

const modelCatalogSchema = z.object({
  providers: z.array(providerSchema),
  models: z.array(modelSchema),
});

/** The models the platform offers, each with the parameters it admits (R1.4.2). */
export const useModelCatalog = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['models'],
    queryFn: async () => readData(await api.GET('/models'), modelCatalogSchema),
  });
};
