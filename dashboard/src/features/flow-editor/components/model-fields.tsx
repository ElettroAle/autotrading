import { useFormContext, useWatch } from 'react-hook-form';
import { Link } from 'react-router';

import { describedBy, FieldError, FORM_CONTROL, FormField } from '@/components/ui/form/form-field';
import { SelectField, type SelectOptionGroup } from '@/components/ui/form/select-field';
import { paths } from '@/config/paths';
import { reasonOf } from '@/lib/form-errors';

import type { Model, ModelParameter, Provider } from '../api/get-model-catalog';
import type { FlowFormValues } from '../utils/flow-form';
import { missesProviderKey, modelGroupsOf, type ModelGroup } from '../utils/model-groups';

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
            className={FORM_CONTROL}
          />
        ) : (
          <select {...control} {...register(name)} className={FORM_CONTROL}>
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

const choicesOf = (group: ModelGroup): SelectOptionGroup => ({
  label: `${group.provider} · chiave ${group.keyRegistered ? 'registrata' : 'mancante'}`,
  options: group.models.map((model) => ({
    value: model.name,
    label: model.name,
    disabled: !model.selectable,
  })),
});

type ModelFieldsProps = {
  readonly models: Model[];
  readonly providers: Provider[];
  /** The model the flow already has, which stays choosable even when its provider lost the key (ADR 0151). */
  readonly currentModel: string;
};

/**
 * The model of the catalog with the parameters it admits: temperature, tokens, reasoning (R1.4.2, ADR 0131). The
 * models are grouped by provider, with whether its key is registered (R2.3.7, ADR 0151).
 */
export const ModelFields = ({ models, providers, currentModel }: ModelFieldsProps) => {
  const {
    register,
    setValue,
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const selected = useWatch({ control, name: 'model' });
  const model = models.find((candidate) => candidate.name === selected);
  const parametersError = reasonOf(errors.model_parameters);
  const groups = modelGroupsOf(models, providers, currentModel);
  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="font-semibold">Modello</legend>
      <SelectField
        id="flow-model"
        label="Modello"
        placeholder="Scegli un modello"
        choices={groups.map(choicesOf)}
        error={errors.model}
        {...register('model', {
          // The parameters belong to the model: a new model starts from its own defaults.
          onChange: () => setValue('model_parameters', {}),
        })}
      />
      {missesProviderKey(groups) && (
        <p className="text-sm text-slate-600">
          I modelli di un fornitore senza chiave non si possono scegliere:{' '}
          <Link to={paths.providerKeys.getHref()} className="text-blue-800 hover:underline">
            Chiavi dei fornitori IA
          </Link>
        </p>
      )}
      {model !== undefined && model.parameters.length > 0 && (
        <div
          role="group"
          aria-label="Parametri del modello"
          className="flex min-w-0 flex-wrap gap-4"
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
