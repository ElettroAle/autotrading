import { z } from 'zod';

/**
 * The previous operative decisions of a flow on one asset, from the most recent, as the API gives them: on the flow
 * what the agent will receive, in a cycle what it received (R5.3.4). No price without an execution, no outcome without
 * a position.
 */
export const assetMemorySchema = z.object({
  asset: z.string(),
  decisions: z.array(
    z.object({
      planned_at: z.string(),
      action: z.string(),
      direction: z.string().nullable(),
      price: z.string().nullable(),
      reasoning: z.string(),
      outcome: z.object({ pnl: z.string(), realized: z.boolean() }).nullable(),
    }),
  ),
});

export type AssetMemory = z.infer<typeof assetMemorySchema>;
