import { AgentContextOption } from './agent-context-option';

const HINT_ID = 'flow-account-exposure-for-agent-hint';

/**
 * The option that shows the agent the exposure of the other flows of the same account, beside the other options of
 * the context of the agent; off, the agent sees the flow alone (R5.5.5, ADR esposizione-del-conto-nella-dashboard).
 */
export const AccountExposureField = () => (
  <AgentContextOption
    name="account_exposure_for_agent"
    aria-describedby={HINT_ID}
    hint="lo stato inviato all'agente riporta il valore long e short delle posizioni degli altri flussi dello stesso conto"
  >
    Esposizione degli altri flussi del conto nel contesto dell&apos;agente
  </AgentContextOption>
);
