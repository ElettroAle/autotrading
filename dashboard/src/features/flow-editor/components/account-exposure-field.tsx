import { useFormContext } from 'react-hook-form';

import type { FlowFormValues } from '../utils/flow-form';

const HINT_ID = 'flow-account-exposure-for-agent-hint';

/**
 * The option that shows the agent the exposure of the other flows of the same account, beside the other options of
 * the context of the agent; off, the agent sees the flow alone (R5.5.5, ADR esposizione-del-conto-nella-dashboard).
 */
export const AccountExposureField = () => {
  const { register } = useFormContext<FlowFormValues>();
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          {...register('account_exposure_for_agent')}
          aria-describedby={HINT_ID}
        />
        Esposizione degli altri flussi del conto nel contesto dell&apos;agente
      </label>
      <p id={HINT_ID} className="text-xs text-slate-600">
        lo stato inviato all&apos;agente riporta il valore long e short delle posizioni degli altri
        flussi dello stesso conto
      </p>
    </div>
  );
};
