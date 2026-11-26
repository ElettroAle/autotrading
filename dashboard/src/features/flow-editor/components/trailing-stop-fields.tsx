import { useFormContext } from 'react-hook-form';

import { CheckboxField } from '@/components/ui/form/checkbox-field';
import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import { FLOW_FIELD_INFO } from '../utils/field-info';
import type { FlowFormValues } from '../utils/flow-form';

type TrailingPart = 'distance_percent' | 'activation_percent' | 'breakeven_percent';

// Each part with what it admits; the API checks the values and their combination (ADR
// stop-che-segue-il-prezzo-nella-dashboard).
const PARTS: readonly {
  part: TrailingPart;
  id: string;
  label: string;
  info: string;
  hint: string;
}[] = [
  {
    part: 'distance_percent',
    id: 'flow-trailing-distance',
    label: 'Distanza dello stop che segue (%)',
    info: FLOW_FIELD_INFO.trailingDistance,
    hint: 'da 0,1 a 50, dal miglior prezzo raggiunto; vuota: lo stop non segue il prezzo',
  },
  {
    part: 'activation_percent',
    id: 'flow-trailing-activation',
    label: 'Attivazione (%)',
    info: FLOW_FIELD_INFO.trailingActivation,
    hint: "maggiore di 0, solo con la distanza; vuota: lo stop segue dall'apertura",
  },
  {
    part: 'breakeven_percent',
    id: 'flow-trailing-breakeven',
    label: 'Pareggio (%)',
    info: FLOW_FIELD_INFO.trailingBreakeven,
    hint: "maggiore di 0; raggiunta, lo stop va al prezzo d'ingresso",
  },
];

const MAX_PROFIT_ID = 'flow-trailing-max-profit';

/**
 * The stop that follows the price beside the default protections, each part with what it admits and the reason of a
 * refusal of the API under it (R5.5.1, ADR stop-che-segue-il-prezzo-nella-dashboard).
 */
export const TrailingStopFields = () => {
  const {
    register,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  return (
    <>
      {PARTS.map(({ part, id, label, info, hint }) => (
        <FormField
          key={part}
          id={id}
          label={label}
          info={info}
          error={errors.trailing_stop?.[part]?.message}
          hint={hint}
        >
          {(control) => (
            <input
              {...control}
              {...register(`trailing_stop.${part}`)}
              inputMode="decimal"
              className={FORM_CONTROL}
            />
          )}
        </FormField>
      ))}
      <CheckboxField
        id={MAX_PROFIT_ID}
        label="Massimo profitto raggiunto nel contesto dell'agente"
        info={FLOW_FIELD_INFO.maxProfitInContext}
        hint="ha effetto solo con la distanza o il pareggio"
        {...register('trailing_stop.max_profit_in_context')}
      />
    </>
  );
};
