import type { ReactNode } from 'react';
import { useFormContext } from 'react-hook-form';

import type { FlowFormValues } from '../utils/flow-form';

type AgentContextOptionProps = {
  readonly name: 'account_exposure_for_agent' | 'fees_for_agent';
  /** The id of the line that says what the option adds to the state sent to the agent. */
  readonly 'aria-describedby': string;
  readonly hint: string;
  readonly children: ReactNode;
};

/**
 * A switch of the context of the agent with the line that says what it adds to the state sent to the agent; off, the
 * agent receives what it received before (R5.5.5, R5.5.6).
 */
export const AgentContextOption = ({
  name,
  'aria-describedby': hintId,
  hint,
  children,
}: AgentContextOptionProps) => {
  const { register } = useFormContext<FlowFormValues>();
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2">
        <input type="checkbox" {...register(name)} aria-describedby={hintId} />
        {children}
      </label>
      <p id={hintId} className="text-xs text-slate-600">
        {hint}
      </p>
    </div>
  );
};
