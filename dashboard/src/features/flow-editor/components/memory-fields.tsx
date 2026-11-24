import { useFormContext, useWatch } from 'react-hook-form';

import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import type { FlowFormValues } from '../utils/flow-form';

/**
 * The memory of the flow: the switch, then how many previous decisions per asset and of how many days, which count
 * only with the memory on (R5.3.4, ADR memoria-del-flusso-dalle-decisioni-operative-precedenti).
 */
export const MemoryFields = () => {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const active = useWatch({ control, name: 'memory.active' });
  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="font-semibold">Memoria</legend>
      <label className="flex items-center gap-2">
        <input type="checkbox" {...register('memory.active')} />
        Memoria attiva
      </label>
      <FormField
        id="flow-memory-decisions"
        label="Decisioni per asset"
        error={errors.memory?.decisions?.message}
      >
        {(fieldControl) => (
          <input
            {...fieldControl}
            {...register('memory.decisions')}
            disabled={!active}
            inputMode="numeric"
            className={FORM_CONTROL}
          />
        )}
      </FormField>
      <FormField id="flow-memory-days" label="Giorni" error={errors.memory?.days?.message}>
        {(fieldControl) => (
          <input
            {...fieldControl}
            {...register('memory.days')}
            disabled={!active}
            inputMode="numeric"
            className={FORM_CONTROL}
          />
        )}
      </FormField>
    </fieldset>
  );
};
