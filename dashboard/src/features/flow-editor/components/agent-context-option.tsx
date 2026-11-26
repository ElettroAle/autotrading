import { useFormContext } from 'react-hook-form';

import { CheckboxField } from '@/components/ui/form/checkbox-field';

import type { FlowFormValues } from '../utils/flow-form';

type AgentContextOptionProps = {
  readonly name: 'account_exposure_for_agent' | 'fees_for_agent';
  /** The id of the option: `<id>-hint` is the line that says what it adds to the state sent to the agent. */
  readonly id: string;
  readonly label: string;
  readonly info: string;
  readonly hint: string;
};

/**
 * A switch of the context of the agent with the line that says what it adds to the state sent to the agent; off, the
 * agent receives what it received before (R5.5.5, R5.5.6).
 */
export const AgentContextOption = ({ name, id, label, info, hint }: AgentContextOptionProps) => {
  const { register } = useFormContext<FlowFormValues>();
  return <CheckboxField id={id} label={label} info={info} hint={hint} {...register(name)} />;
};
