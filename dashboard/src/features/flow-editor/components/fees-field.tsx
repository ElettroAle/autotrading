import { AgentContextOption } from './agent-context-option';

const HINT_ID = 'flow-fees-for-agent-hint';

/**
 * The option that gives the agent the round-trip cost of a position, beside the other options of the context of the
 * agent; off, the agent receives what it received before (R5.5.6, ADR
 * costo-di-andata-e-ritorno-nel-contesto-dell-agente).
 */
export const FeesField = () => (
  <AgentContextOption
    name="fees_for_agent"
    aria-describedby={HINT_ID}
    hint="lo stato inviato all'agente riporta il costo di andata e ritorno: la commissione del conto per un ordine a mercato, contata per l'apertura e per la chiusura"
  >
    Commissioni nel contesto dell&apos;agente
  </AgentContextOption>
);
