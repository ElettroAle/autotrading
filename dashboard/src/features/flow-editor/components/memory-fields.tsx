import { useFormContext, useWatch } from 'react-hook-form';

import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import type { FlowFormValues } from '../utils/flow-form';

/**
 * The memory of the flow: the switch, then how many previous decisions per asset and of how many days, how long the
 * motive of each and whether it remembers every decision, which count only with the memory on (R5.3.4, R5.3.5, ADR
 * memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni). An unlimited length leaves the motive whole.
 * Then the summary of the closed positions and that of the other assets of the flow, also only with the memory on
 * (R5.3.7, ADR opzioni-della-memoria-nella-dashboard).
 */
type MemoryOptionProps = {
  readonly name: 'memory.summary' | 'memory.other_assets';
  readonly label: string;
  readonly hint: string;
  readonly disabled: boolean;
};

// A switch of the memory with the line that says what it adds.
const MemoryOption = ({ name, label, hint, disabled }: MemoryOptionProps) => {
  const { register } = useFormContext<FlowFormValues>();
  const hintId = `flow-${name.replace('.', '-').replace('_', '-')}-hint`;
  return (
    <>
      <label className="flex items-center gap-2">
        <input type="checkbox" {...register(name)} disabled={disabled} aria-describedby={hintId} />
        {label}
      </label>
      <p id={hintId} className="text-xs text-slate-600">
        {hint}
      </p>
    </>
  );
};

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
        hint="caratteri del motivo di ogni decisione ricordata"
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
        <input
          type="checkbox"
          {...register('memory.all_decisions')}
          disabled={!active}
          aria-describedby="flow-memory-all-decisions-hint"
        />
        Tutte le decisioni
      </label>
      <p id="flow-memory-all-decisions-hint" className="text-xs text-slate-600">
        spenta: solo aperture, chiusure e inversioni; accesa: anche aggiornamenti e decisioni di
        mantenere
      </p>
      <MemoryOption
        name="memory.summary"
        label="Riepilogo per asset e direzione"
        hint="in testa alla memoria di ogni asset, una riga per direzione con le posizioni chiuse nei giorni della memoria"
        disabled={!active}
      />
      <MemoryOption
        name="memory.other_assets"
        label="Altri asset del flusso"
        hint="nella memoria di ogni asset, le righe di riepilogo degli altri asset del flusso, senza le loro decisioni"
        disabled={!active}
      />
    </fieldset>
  );
};
