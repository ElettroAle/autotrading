import { z } from 'zod';

// What the steps of a cycle produced, as the journal of the worker records it (R1.7.1). The API gives each document as
// free JSON: a document of another shape is still shown, as it is.

const openingSchema = z.object({ direction: z.string() });

const decisionSchema = z.object({
  asset: z.string(),
  action: z.string(),
  reasoning: z.string(),
  opening: openingSchema.nullish(),
});

const agentDecisionSchema = z.object({
  risposta: z.string(),
  decisioni: z.array(decisionSchema),
  scartate: z.array(z.unknown()),
  mancanti: z.array(z.string()),
});

const contextSchema = z.object({
  messaggi: z.array(z.object({ ruolo: z.string(), contenuto: z.string() })),
});

const sourcesSchema = z.object({
  fonti: z.array(z.object({ fonte: z.string(), dati: z.unknown() })),
});

export type Decision = z.infer<typeof decisionSchema>;
export type AgentDecision = z.infer<typeof agentDecisionSchema>;
export type ContextMessage = z.infer<typeof contextSchema>['messaggi'][number];
export type SourceReading = z.infer<typeof sourcesSchema>['fonti'][number];

export const decisionsOf = (content: unknown): AgentDecision | undefined =>
  agentDecisionSchema.safeParse(content).data;

export const contextOf = (content: unknown): ContextMessage[] | undefined =>
  contextSchema.safeParse(content).data?.messaggi;

export const sourcesOf = (content: unknown): SourceReading[] | undefined =>
  sourcesSchema.safeParse(content).data?.fonti;

export const decisionLabelOf = (decision: Decision): string =>
  [decision.action, decision.opening?.direction, decision.asset]
    .filter((part) => part !== undefined)
    .join(' ');

/** The decisions of the agent in a few words each, «apri long BTC»; none when the cycle never got to the agent. */
export const decisionLabelsOf = (content: unknown): string[] =>
  decisionsOf(content)?.decisioni.map(decisionLabelOf) ?? [];
