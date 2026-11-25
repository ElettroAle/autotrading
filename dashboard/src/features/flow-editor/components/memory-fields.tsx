import { useFormContext, useWatch } from 'react-hook-form';

import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import type { FlowFormValues } from '../utils/flow-form';

/**
 * The memory of the flow: the switch, then how many previous decisions per asset and of how many days, how long the
 * motive of each and whether it remembers every decision, which count only with the memory on (R5.3.4, R5.3.5, ADR
 * memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni). An unlimited length leaves the motive whole.
 */
export const MemoryFields = () => {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const active = useWatch({ control, name: 'memory.active' });
  const unlimited = useWatch({ control, name: 'memory.unlimited_text_length' });
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
      <FormField
        id="flow-memory-text-length"
        label="Lunghezza del motivo"
        error={errors.memory?.text_length?.message}
      >
        {(fieldControl) => (
          <input
            {...fieldControl}
            {...register('memory.text_length')}
            disabled={!active || unlimited === true}
            inputMode="numeric"
            className={FORM_CONTROL}
          />
        )}
      </FormField>
      <label className="flex items-center gap-2">
        <input type="checkbox" {...register('memory.unlimited_text_length')} disabled={!active} />
        Lunghezza illimitata
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" {...register('memory.all_decisions')} disabled={!active} />
        Tutte le decisioni
      </label>
    </fieldset>
  );
};
