import { useFormContext } from 'react-hook-form';

import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import { LOSS_COUNT_SCOPES, type FlowFormValues } from '../utils/flow-form';

type LimitPart = 'max_consecutive_losses' | 'loss_window_hours' | 'block_minutes';

// Each part with what it admits; the API checks the values and that the three go together (ADR
// blocco-delle-riaperture-nella-dashboard).
const PARTS: readonly { part: LimitPart; id: string; label: string; hint: string }[] = [
  {
    part: 'max_consecutive_losses',
    id: 'flow-loss-limit-losses',
    label: 'Perdite consecutive massime',
    hint: 'intero da 1 in su, con finestra e durata; vuote tutte e tre: nessun blocco',
  },
  {
    part: 'loss_window_hours',
    id: 'flow-loss-limit-window',
    label: 'Finestra delle perdite (ore)',
    hint: 'intero da 1 in su: le chiusure più vecchie non contano',
  },
  {
    part: 'block_minutes',
    id: 'flow-loss-limit-block',
    label: 'Durata del blocco (minuti)',
    hint: "intero da 1 in su, dall'ultima perdita contata",
  },
];

const SCOPE_LABELS: Record<(typeof LOSS_COUNT_SCOPES)[number], string> = {
  asset: 'per singolo asset',
  flusso: 'su tutto il flusso',
};

/**
 * The block of the reopenings after consecutive losses beside the maximum losses, each part with what it admits and
 * the reason of a refusal of the API under it (R5.5.2, ADR blocco-delle-riaperture-nella-dashboard).
 */
export const ConsecutiveLossFields = () => {
  const {
    register,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const refused = errors.consecutive_loss_limit;
  return (
    <>
      {PARTS.map(({ part, id, label, hint }) => (
        <FormField key={part} id={id} label={label} error={refused?.[part]?.message} hint={hint}>
          {(control) => (
            <input
              {...control}
              {...register(`consecutive_loss_limit.${part}`)}
              inputMode="numeric"
              className={FORM_CONTROL}
            />
          )}
        </FormField>
      ))}
      <FormField
        id="flow-loss-limit-scope"
        label="Ambito del conteggio"
        error={refused?.count_scope?.message}
        hint="le perdite si contano e si bloccano su ogni asset, o su tutti gli asset del flusso"
      >
        {(control) => (
          <select
            {...control}
            {...register('consecutive_loss_limit.count_scope')}
            className={FORM_CONTROL}
          >
            {LOSS_COUNT_SCOPES.map((scope) => (
              <option key={scope} value={scope}>
                {SCOPE_LABELS[scope]}
              </option>
            ))}
          </select>
        )}
      </FormField>
    </>
  );
};
