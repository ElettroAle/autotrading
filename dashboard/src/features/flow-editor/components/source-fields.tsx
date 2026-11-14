import { useFormContext, useWatch } from 'react-hook-form';

import { ErrorMessage } from '@/components/ui/error-message';
import { describedBy, FieldError, FORM_CONTROL, FormField } from '@/components/ui/form/form-field';
import { Loading } from '@/components/ui/loading';
import { reasonOf } from '@/lib/form-errors';

import { useSource, type Source } from '../api/get-sources';
import type { FlowFormValues } from '../utils/flow-form';

const SOURCES_ID = 'flow-sources';

// The parameters a source admits come from its description in the catalog, never from the dashboard (ADR 0131).
const SourceParameters = ({ name }: { name: string }) => {
  const {
    register,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const source = useSource(name);
  if (source.isPending) {
    return <Loading />;
  }
  if (source.isError) {
    return <ErrorMessage error={source.error} />;
  }
  return source.data.parameters.map((parameter) => (
    <FormField
      key={parameter.key}
      id={`flow-source-${name}-${parameter.key}`}
      label={`${parameter.label} di ${name}`}
      error={errors.sources?.[name]?.parameters?.[parameter.key]?.message}
    >
      {(control) => (
        <input
          {...control}
          {...register(`sources.${name}.parameters.${parameter.key}`)}
          type="number"
          min={parameter.minimum}
          max={parameter.maximum}
          placeholder={String(parameter.default)}
          className={FORM_CONTROL}
        />
      )}
    </FormField>
  ));
};

const SourceChoice = ({ source }: { source: Source }) => {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const active = useWatch({ control, name: `sources.${source.name}.active` }) === true;
  const id = `flow-source-${source.name}`;
  return (
    <div className="min-w-0 space-y-2 border-t border-slate-100 pt-2">
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="checkbox"
          aria-describedby={`${id}-description`}
          {...register(`sources.${source.name}.active`)}
        />
        <label htmlFor={id} className="font-medium">
          {source.name}
        </label>
      </div>
      <p id={`${id}-description`} className="text-sm text-slate-600">
        {source.description}
      </p>
      {active && (
        <div className="flex min-w-0 flex-wrap gap-4">
          <FormField
            id={`${id}-weight`}
            label={`Peso di ${source.name}`}
            error={errors.sources?.[source.name]?.weight?.message}
          >
            {(props) => (
              <input
                {...props}
                {...register(`sources.${source.name}.weight`)}
                type="number"
                min={1}
                max={10}
                className={FORM_CONTROL}
              />
            )}
          </FormField>
          <SourceParameters name={source.name} />
        </div>
      )}
    </div>
  );
};

/** The sources of the catalog, each active or not with its weight and its parameters (R1.3.1, R1.3.2). */
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
