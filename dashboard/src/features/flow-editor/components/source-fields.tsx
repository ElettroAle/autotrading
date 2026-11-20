import { useFormContext, useWatch } from 'react-hook-form';

import { describedBy, FieldError, FORM_CONTROL, FormField } from '@/components/ui/form/form-field';
import { reasonOf } from '@/lib/form-errors';

import type { Source, SourceAdapter, SourceParameter } from '../api/get-sources';
import { adapterKeyOf, type FlowFormValues } from '../utils/flow-form';

const SOURCES_ID = 'flow-sources';
const NO_CONFIGURATION = 'nessuna configurazione necessaria';

// A parameter with choices names its default by its label; blank keeps the default of the catalog.
const defaultLabelOf = (parameter: SourceParameter): string =>
  parameter.choices.find((choice) => choice.value === parameter.default)?.label ??
  String(parameter.default);

// Weight and parameters of an adapter chosen: the parameters come from its declaration in the catalog, never from the
// dashboard (ADR 0131, ADR scelta-degli-adapter-nell-editor-del-flusso).
const AdapterSettings = ({ source, adapter }: { source: Source; adapter: SourceAdapter }) => {
  const {
    register,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const key = adapterKeyOf(adapter.name);
  const path = `sources.${source.name}.adapters.${key}` as const;
  const adapterErrors = errors.sources?.[source.name]?.adapters?.[key];
  const id = `flow-source-${source.name}-${key}`;
  const label = `${source.name} · ${adapter.name}`;
  return (
    <div className="flex min-w-0 flex-wrap gap-4">
      <FormField
        id={`${id}-weight`}
        label={`Peso di ${label}`}
        error={adapterErrors?.weight?.message}
      >
        {(props) => (
          <input
            {...props}
            {...register(`${path}.weight`)}
            type="number"
            min={1}
            max={10}
            className={FORM_CONTROL}
          />
        )}
      </FormField>
      {adapter.parameters.map((parameter) => (
        <FormField
          key={parameter.key}
          id={`${id}-${parameter.key}`}
          label={`${parameter.label} di ${label}`}
          error={adapterErrors?.parameters?.[parameter.key]?.message}
        >
          {(control) =>
            parameter.choices.length === 0 ? (
              <input
                {...control}
                {...register(`${path}.parameters.${parameter.key}`)}
                type="number"
                min={parameter.minimum}
                max={parameter.maximum}
                placeholder={String(parameter.default)}
                className={FORM_CONTROL}
              />
            ) : (
              <select
                {...control}
                {...register(`${path}.parameters.${parameter.key}`)}
                className={FORM_CONTROL}
              >
                <option value="">{`predefinito (${defaultLabelOf(parameter)})`}</option>
                {parameter.choices.map((choice) => (
                  <option key={choice.value} value={choice.value}>
                    {choice.label}
                  </option>
                ))}
              </select>
            )
          }
        </FormField>
      ))}
    </div>
  );
};

// An adapter of an active source: its choice, what it declares of itself and, once chosen, its settings (R4.1.1); one
// the tenant did not configure says why it cannot be chosen, and only the flow that already has it can drop it (R4.1.2).
const AdapterChoice = ({ source, adapter }: { source: Source; adapter: SourceAdapter }) => {
  const { register, control } = useFormContext<FlowFormValues>();
  const key = adapterKeyOf(adapter.name);
  const chosen =
    useWatch({ control, name: `sources.${source.name}.adapters.${key}.active` }) === true;
  const id = `flow-source-${source.name}-${key}`;
  const configuration =
    adapter.configuration_fields.length === 0
      ? NO_CONFIGURATION
      : adapter.configuration_fields.map((field) => field.label).join(', ');
  const unavailable = adapter.unavailable_reason !== null && !chosen;
  return (
    <li className="min-w-0 space-y-2">
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="checkbox"
          aria-describedby={`${id}-description`}
          disabled={unavailable}
          {...register(`sources.${source.name}.adapters.${key}.active`)}
        />
        <label htmlFor={id} className="font-medium break-words">
          {adapter.name}
        </label>
      </div>
      <div id={`${id}-description`} className="space-y-1 text-sm text-slate-600">
        <p>{adapter.description}</p>
        <p>{configuration}</p>
        {adapter.unavailable_reason !== null && (
          <p className="text-amber-800">{adapter.unavailable_reason}</p>
        )}
      </div>
      {chosen && <AdapterSettings source={source} adapter={adapter} />}
    </li>
  );
};

const SourceChoice = ({ source }: { source: Source }) => {
  const { register, control, setValue } = useFormContext<FlowFormValues>();
  const active = useWatch({ control, name: `sources.${source.name}.active` }) === true;
  const id = `flow-source-${source.name}`;
  const [onlyAdapter] = source.adapters.length === 1 ? source.adapters : [];
  // A source with a single adapter has it chosen as soon as it is activated (ADR scelta-degli-adapter-nell-editor).
  const activation = register(`sources.${source.name}.active`, {
    onChange: (event: { target: { checked: boolean } }) => {
      if (event.target.checked && onlyAdapter !== undefined) {
        setValue(`sources.${source.name}.adapters.${adapterKeyOf(onlyAdapter.name)}.active`, true);
      }
    },
  });
  return (
    <div className="min-w-0 space-y-2 border-t border-slate-100 pt-2">
      <div className="flex items-center gap-2">
        <input id={id} type="checkbox" aria-describedby={`${id}-description`} {...activation} />
        <label htmlFor={id} className="font-medium">
          {source.name}
        </label>
      </div>
      <p id={`${id}-description`} className="text-sm text-slate-600">
        {source.description}
      </p>
      {active && (
        <ul aria-label={`Adapter di ${source.name}`} className="min-w-0 space-y-3 pl-6">
          {source.adapters.map((adapter) => (
            <AdapterChoice key={adapter.name} source={source} adapter={adapter} />
          ))}
        </ul>
      )}
    </div>
  );
};

/**
 * The sources of the catalog, each active or not with the adapters chosen, each with its weight and its parameters
 * (R1.3.1, R1.3.2, R4.1.1).
 */
export const SourceFields = ({ sources }: { sources: Source[] }) => {
  const {
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const error = reasonOf(errors.sources);
  return (
    <fieldset className="min-w-0 space-y-2" {...describedBy(SOURCES_ID, error)}>
      <legend className="font-semibold">Fonti</legend>
      {sources.map((source) => (
        <SourceChoice key={source.name} source={source} />
      ))}
      <FieldError id={SOURCES_ID} error={error} />
    </fieldset>
  );
};
