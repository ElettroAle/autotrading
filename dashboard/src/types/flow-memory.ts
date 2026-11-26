import { z } from 'zod';

/**
 * The previous decisions of a flow on one asset, from the most recent, as the API gives them: on the flow what the
 * agent will receive, in a cycle what it received (R5.3.4). No price without an execution, no outcome without a
 * position; the motive in one sentence, the invalidation of an opening and the course of its position (R5.3.5).
 * Before them, with the options of the memory on, the summary lines of the asset and of the other assets of the flow,
 * as the agent receives them (R5.3.7).
 */
export const assetMemorySchema = z.object({
  asset: z.string(),
  summary: z.array(z.string()),
  other_assets: z.array(z.string()),
  entries: z.array(
    z.object({
      planned_at: z.string(),
      action: z.string(),
      direction: z.string().nullable(),
      price: z.string().nullable(),
      motive: z.string(),
      invalidation: z.string().nullable(),
      outcome: z
        .object({
          pnl: z.string(),
          realized: z.boolean(),
          course: z.string().nullable().optional(),
        })
        .nullable(),
    }),
  ),
});

export type AssetMemory = z.infer<typeof assetMemorySchema>;
