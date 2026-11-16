import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

/** A placeholder the system prompt may use, as the registry of the platform declares it (R1.4.8). */
export const promptPlaceholderSchema = z.object({ name: z.string(), description: z.string() });

export type PromptPlaceholder = z.infer<typeof promptPlaceholderSchema>;

const defaultSystemPromptSchema = z.object({
  system_prompt: z.string(),
  system_prompt_placeholders: z.array(promptPlaceholderSchema),
});

export type DefaultSystemPrompt = z.infer<typeof defaultSystemPromptSchema>;

/** The system prompt a flow follows until the user writes their own, with the placeholders it may use (R1.4.8). */
export const useDefaultSystemPrompt = () => {
  const api = useApiClient();
  return useQuery({
    queryKey: ['flows', 'system-prompt'],
    queryFn: async () => readData(await api.GET('/flows/system-prompt'), defaultSystemPromptSchema),
  });
};
