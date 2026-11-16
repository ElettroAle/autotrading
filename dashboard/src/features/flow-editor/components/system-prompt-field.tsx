import { useFormContext, useWatch } from 'react-hook-form';

import { FORM_TEXT_AREA, FormField } from '@/components/ui/form/form-field';

import type { DefaultSystemPrompt } from '../api/get-system-prompt';
import type { FlowFormValues } from '../utils/flow-form';

const FIELD_ID = 'flow-system-prompt';
const PLACEHOLDERS_ID = `${FIELD_ID}-placeholders`;

/**
 * The system prompt of the flow: the default of the platform until the user writes over it, with the way back to the
 * default and, below, the placeholders the API declares with what each stands for (R1.4.8).
 */
export const SystemPromptField = ({ systemPrompt }: { systemPrompt: DefaultSystemPrompt }) => {
  const {
    control,
    setValue,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const [text, followsDefault] = useWatch({
    control,
    name: ['system_prompt', 'system_prompt_default'],
  });
  const write = (written: string) => {
    setValue('system_prompt', written, { shouldDirty: true });
    setValue('system_prompt_default', false, { shouldDirty: true });
  };
  const restoreDefault = () => {
    setValue('system_prompt', '', { shouldDirty: true });
    setValue('system_prompt_default', true, { shouldDirty: true });
  };

  return (
    <div className="min-w-0 space-y-2">
      <FormField id={FIELD_ID} label="System prompt" error={errors.system_prompt?.message}>
        {(controlProps) => (
          <textarea
            {...controlProps}
            aria-describedby={[controlProps['aria-describedby'], PLACEHOLDERS_ID]
              .filter((id) => id !== undefined)
              .join(' ')}
            value={followsDefault ? systemPrompt.system_prompt : text}
            onChange={(event) => {
              write(event.target.value);
            }}
            rows={12}
            className={`${FORM_TEXT_AREA} font-mono text-sm`}
          />
        )}
      </FormField>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {followsDefault ? (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-700">predefinito</span>
        ) : (
          <button
            type="button"
            onClick={restoreDefault}
            className="rounded border border-slate-300 px-2 py-0.5"
          >
            Ripristina predefinito
          </button>
        )}
      </div>
      <dl id={PLACEHOLDERS_ID} className="space-y-1 text-sm text-slate-600">
        {systemPrompt.system_prompt_placeholders.map((placeholder) => (
          <div key={placeholder.name} className="flex min-w-0 flex-wrap gap-x-2">
            <dt className="font-mono">{`{${placeholder.name}}`}</dt>
            <dd>{placeholder.description}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
};
