import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import {
  useForm,
  useWatch,
  type Path,
  type Resolver,
  type UseFormRegisterReturn,
} from 'react-hook-form';

import { CommandButton } from '@/components/ui/command-button';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { SelectField, type UnavailableList } from '@/components/ui/form/select-field';
import { showRefusal } from '@/lib/form-errors';
import { choiceOptionsOf, hasChoices } from '@/lib/parameter-choices';
import { isList, listRangeOf } from '@/lib/parameter-lists';

import type { TrialSource } from '../api/get-trial-sources';
import { useTrySourceAdapter } from '../api/try-source-adapter';
import {
  adapterNamed,
  defaultParametersOf,
  initialValuesOf,
  trialRequestOf,
  trialSchemaOf,
  type TrialFormValues,
} from '../utils/trial-form';

import { SourceTrialOutcome } from './source-trial-outcome';

/** The assets a trial of a source per asset may read, as the list of the exchange arrives. */
export type TrialAssets = {
  readonly names: readonly string[];
  readonly loading: boolean;
  readonly unavailable: UnavailableList | undefined;
};

// The rules follow the adapter chosen: each declares its own parameters and limits (R4.1.1).
const resolverOf =
  (source: TrialSource): Resolver<TrialFormValues> =>
  async (values, context, options) =>
    zodResolver(trialSchemaOf(source, adapterNamed(source, values.adapter)))(
      values,
      context,
      options,
    );

const AdapterChoice = ({
  source,
  error,
  field,
}: {
  readonly source: TrialSource;
  readonly error: { readonly message?: string } | undefined;
  readonly field: UseFormRegisterReturn<'adapter'>;
}) => {
  const [only] = source.adapters;
  if (source.adapters.length === 1 && only !== undefined) {
    return (
      <p className="text-sm">
        <span className="text-slate-600">Adapter:</span> {only.name}
      </p>
    );
  }
  return (
    <SelectField
      label="Adapter"
      placeholder="Scegli l'adapter"
      choices={source.adapters.map((adapter) => ({ value: adapter.name, label: adapter.name }))}
      error={error}
      {...field}
    />
  );
};

/**
 * The trial of a source: the adapter, the asset for a source per asset and every parameter at its default; a value
 * outside the limits of the catalog stops the trial before it leaves (ADR pagina-fonti-con-la-prova).
 */
export const SourceTrialForm = ({
  source,
  assets,
}: {
  readonly source: TrialSource;
  readonly assets: TrialAssets;
}) => {
  const trial = useTrySourceAdapter();
  const {
    register,
    handleSubmit,
    getValues,
    reset,
    setValue,
    setError,
    control,
    formState: { errors },
  } = useForm<TrialFormValues>({
    resolver: resolverOf(source),
    defaultValues: initialValuesOf(source),
  });
  const adapter = adapterNamed(source, useWatch({ control, name: 'adapter' }));
  const firstAsset = assets.names[0];

  // The first asset of the exchange is chosen for the user, who changes it only to try another.
  useEffect(() => {
    if (source.per_asset && firstAsset !== undefined && getValues('asset') === '') {
      setValue('asset', firstAsset);
    }
  }, [source.per_asset, firstAsset, getValues, setValue]);

  // Another adapter brings its own parameters, at their defaults.
  const adapterField = register('adapter', {
    onChange: (event: { target: { value: string } }) => {
      reset({
        ...getValues(),
        adapter: event.target.value,
        parameters: defaultParametersOf(adapterNamed(source, event.target.value)),
      });
    },
  });

  const fieldOf = (field: string): Path<TrialFormValues> | undefined => {
    if (field === 'asset') {
      return 'asset';
    }
    return adapter?.parameters.some((parameter) => parameter.key === field)
      ? `parameters.${field}`
      : undefined;
  };

  const onSubmit = handleSubmit((values) => {
    trial.mutate(trialRequestOf(source, values), {
      onError: (error) => {
        showRefusal(error, setError, fieldOf);
      },
    });
  });

  return (
    <>
      <form
        aria-label={`Prova di ${source.name}`}
        onSubmit={(event) => void onSubmit(event)}
        noValidate
        className="space-y-3"
      >
        <FormAlert error={errors.root?.server} />
        <AdapterChoice source={source} error={errors.adapter} field={adapterField} />
        {source.per_asset && (
          <SelectField
            label="Asset"
            placeholder="Scegli l'asset"
            choices={assets.names.map((name) => ({ value: name, label: name }))}
            loading={assets.loading}
            unavailable={assets.unavailable}
            error={errors.asset}
            {...register('asset')}
          />
        )}
        {adapter?.parameters.map((parameter) =>
          isList(parameter) ? (
            <InputField
              key={`${adapter.name}-${parameter.key}`}
              label={parameter.label}
              type="text"
              inputMode="numeric"
              hint={listRangeOf(parameter)}
              error={errors.parameters?.[parameter.key]}
              {...register(`parameters.${parameter.key}`)}
            />
          ) : hasChoices(parameter) ? (
            <SelectField
              key={`${adapter.name}-${parameter.key}`}
              label={parameter.label}
              placeholder={`Scegli ${parameter.label}`}
              choices={choiceOptionsOf(parameter)}
              error={errors.parameters?.[parameter.key]}
              {...register(`parameters.${parameter.key}`)}
            />
          ) : (
            <InputField
              key={`${adapter.name}-${parameter.key}`}
              label={parameter.label}
              type="number"
              inputMode="numeric"
              min={parameter.minimum}
              max={parameter.maximum}
              step={1}
              error={errors.parameters?.[parameter.key]}
              {...register(`parameters.${parameter.key}`)}
            />
          ),
        )}
        <CommandButton tone="primary" type="submit" icon="play" disabled={trial.isPending}>
          Prova
        </CommandButton>
      </form>
      <SourceTrialOutcome source={source.name} trial={trial.data} />
    </>
  );
};
