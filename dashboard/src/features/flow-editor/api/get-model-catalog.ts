import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { useApiClient } from '@/lib/api-client';

// A range has minimum and maximum, a choice its values; the default is always there (R1.4.2).
const modelParameterSchema = z.object({
  key: z.string(),
  label: z.string(),
  default: z.string(),
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

const modelCatalogSchema = z.object({
  providers: z.array(z.object({ name: z.string(), key_registered: z.boolean() })),
  models: z.array(modelSchema),
});

/** The models the platform offers, each with the parameters it admits (R1.4.2). */
export const useModelCatalog = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['models'],
    queryFn: () => api.get('/models', modelCatalogSchema),
  });
};
