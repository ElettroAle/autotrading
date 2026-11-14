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

const sourceSchema = z.object({
  name: z.string(),
  description: z.string(),
  per_asset: z.boolean(),
  parameters: z.array(sourceParameterSchema),
});

export type Source = z.infer<typeof sourceSchema>;

/** The sources of data the platform offers (R1.3.1). */
export const useSources = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['sources'],
    queryFn: async () => readData(await api.GET('/sources'), z.array(sourceSchema)),
  });
};

/** One source with the parameters it admits, as its description in the catalog says (R1.3.2, ADR 0131). */
export const useSource = (name: string) => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['sources', name],
    queryFn: async () =>
      readData(await api.GET('/sources/{name}', { params: { path: { name } } }), sourceSchema),
  });
};
