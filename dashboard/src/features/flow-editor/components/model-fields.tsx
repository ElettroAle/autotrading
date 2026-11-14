import { useFormContext, useWatch } from 'react-hook-form';

import { describedBy, FieldError, FormField } from '@/components/ui/form/form-field';
import { reasonOf } from '@/lib/form-errors';

import type { Model, ModelParameter } from '../api/get-model-catalog';
import type { FlowFormValues } from '../utils/flow-form';

const INPUT = 'rounded border border-slate-300 px-2 py-1';
const PARAMETERS_ID = 'flow-model-parameters';

// A range is a number between its bounds, a choice one of its values; blank keeps the default of the catalog.
const ParameterField = ({ parameter }: { parameter: ModelParameter }) => {
  const { register } = useFormContext<FlowFormValues>();
  const name = `model_parameters.${parameter.key}` as const;
  return (
    <FormField id={`flow-model-${parameter.key}`} label={parameter.label} error={undefined}>
      {(control) =>
        parameter.choices === undefined || parameter.choices === null ? (
          <input
            {...control}
            {...register(name)}
            inputMode={parameter.whole === true ? 'numeric' : 'decimal'}
            placeholder={parameter.default}
            className={INPUT}
          />
        ) : (
          <select {...control} {...register(name)} className={INPUT}>
            <option value="">{`predefinito (${parameter.default})`}</option>
            {parameter.choices.map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        )
      }
    </FormField>
  );
};

/** The model of the catalog with the parameters it admits: temperature, tokens, reasoning (R1.4.2, ADR 0131). */
export const ModelFields = ({ models }: { models: Model[] }) => {
  const {
    register,
    setValue,
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const selected = useWatch({ control, name: 'model' });
  const model = models.find((candidate) => candidate.name === selected);
  const parametersError = reasonOf(errors.model_parameters);
  return (
    <fieldset className="space-y-2">
      <legend className="font-semibold">Modello</legend>
      <FormField id="flow-model" label="Modello" error={errors.model?.message}>
        {(props) => (
          <select
            {...props}
            {...register('model', {
              // The parameters belong to the model: a new model starts from its own defaults.
              onChange: () => setValue('model_parameters', {}),
            })}
            className={INPUT}
          >
            <option value="">Scegli un modello</option>
            {models.map((candidate) => (
              <option key={candidate.name} value={candidate.name}>
                {candidate.name}
              </option>
            ))}
          </select>
        )}
      </FormField>
      {model !== undefined && model.parameters.length > 0 && (
        <div
          role="group"
          aria-label="Parametri del modello"
          className="flex flex-wrap gap-4"
          {...describedBy(PARAMETERS_ID, parametersError)}
        >
          {model.parameters.map((parameter) => (
            <ParameterField key={`${model.name}-${parameter.key}`} parameter={parameter} />
          ))}
        </div>
      )}
      <FieldError id={PARAMETERS_ID} error={parametersError} />
    </fieldset>
  );
};
