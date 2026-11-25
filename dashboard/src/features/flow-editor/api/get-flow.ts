import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { promptPlaceholderSchema } from './get-system-prompt';

// Numbers of the configuration travel as strings, so no precision is lost on the way (ADR 0018).
export const flowSchema = z.object({
  id: z.string(),
  name: z.string(),
  account_id: z.string().nullable(),
  status: z.string(),
  version: z.number(),
  assets: z.array(z.string()),
  cycle_minutes: z.number(),
  model: z.object({ name: z.string(), parameters: z.record(z.string(), z.string()) }),
  // Every active source with the adapters chosen, each with its weight and its parameters (R4.1.1).
  sources: z.array(
    z.object({
      name: z.string(),
      adapters: z.array(
        z.object({
          name: z.string(),
          weight: z.number(),
          // A list parameter arrives as its list (ADR parametri-delle-fonti-come-liste-libere).
          parameters: z.record(z.string(), z.union([z.number(), z.array(z.number())])),
        }),
      ),
    }),
  ),
  instructions: z.string(),
  risk_limits: z.object({
    max_leverage: z.number().nullable(),
    max_margin_exposure_percent: z.string().nullable(),
    max_value_exposure_percent: z.string().nullable(),
    max_total_margin_exposure_percent: z.string().nullable(),
    max_total_value_exposure_percent: z.string().nullable(),
  }),
  default_stop_loss_percent: z.string(),
  default_take_profit_percent: z.string().nullable(),
  minimum_confidence: z.number().nullable(),
  allocated_capital: z.string().nullable(),
  bring_to_minimum: z.boolean(),
  system_prompt: z.string(),
  system_prompt_is_default: z.boolean(),
  system_prompt_placeholders: z.array(promptPlaceholderSchema),
  max_consecutive_failures: z.number().nullable(),
  max_daily_loss_percent: z.string().nullable(),
  max_drawdown_percent: z.string().nullable(),
  openings_resume: z.enum(['manual', 'next_day']),
  // Off unless the user turns it on, with the decisions per asset and the days it holds (R5.3.4).
  memory: z.object({ active: z.boolean(), decisions: z.number(), days: z.number() }),
});

export type Flow = z.infer<typeof flowSchema>;

/**
 * A draft takes account, capital and assets in its configuration; any other flow keeps its account and changes its
 * capital with its own command (ADR bozza-configurata-dall-editor-e-duplica-con-conto).
 */
export const isDraft = (flow: Flow): boolean => flow.status === 'bozza';

/** The flow with the configuration version in force; the API lists only the flows of the tenant (R0.1.3). */
export const useFlow = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    // Its own key under the flows: the list elsewhere keeps less of each flow, and both refresh together.
    queryKey: ['flows', 'configurations'],
    queryFn: async () => readData(await api.GET('/flows'), z.array(flowSchema)),
    select: (flows) => flows.find((flow) => flow.id === flowId),
  });
};
