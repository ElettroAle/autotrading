import { STEPS, type FakeCycle, type FakeDecision } from './cycles';

/**
 * The last decision of a flow as the API gives it (ADR decisioni-del-ciclo-registrate-per-asset): the decisions of
 * its most recent completed cycle that has any, one by asset, read from the document of the decision; null before.
 */

const OPENING = 'apri';
export const COMPLETED = 'concluso';

export const decisionsOf = (cycle: FakeCycle): FakeDecision[] => {
  const document = cycle.documents.find((each) => each.step === STEPS.agentDecision);
  return (document?.content.decisioni as FakeDecision[] | undefined) ?? [];
};

export const decisionResponse = (decision: FakeDecision) => ({
  asset: decision.asset,
  action: decision.action,
  direction: decision.action === OPENING ? (decision.opening?.direction ?? null) : null,
  confidence: decision.confidence ?? null,
  reasoning: decision.reasoning,
});

export const lastDecisionOf = (cycles: FakeCycle[]) => {
  const decided = cycles
    .filter((cycle) => cycle.outcome === COMPLETED && decisionsOf(cycle).length > 0)
    .toSorted((one, other) => Date.parse(other.planned_at) - Date.parse(one.planned_at));
  const latest = decided[0];
  if (latest === undefined) {
    return null;
  }
  return { planned_at: latest.planned_at, decisions: decisionsOf(latest).map(decisionResponse) };
};
