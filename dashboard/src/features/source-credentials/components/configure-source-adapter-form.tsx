import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { CommandButton } from '@/components/ui/command-button';
import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import {
  sourceCredentialsInputSchema,
  useConfigureSourceAdapter,
  type SourceCredentialsInput,
} from '../api/configure-source-adapter';
import type { SourceCredentials } from '../api/get-source-credentials';

type ConfigureSourceAdapterFormProps = {
  readonly credentials: SourceCredentials;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
};

/**
 * The credentials of an adapter, a field for each field it declares: a secret is never shown and never prefilled, so a
 * replacement asks it again; the values that are not secret start from those saved (ADR sezione-fonti-nella-pagina-chiavi).
 */
export const ConfigureSourceAdapterForm = ({
  credentials,
  onSaved,
  onCancel,
}: ConfigureSourceAdapterFormProps) => {
  const configuration = useConfigureSourceAdapter();
  const fields = credentials.configuration_fields;
  const {
    register,
    handleSubmit,
    resetField,
    setError,
    formState: { errors },
  } = useForm<SourceCredentialsInput>({
    resolver: zodResolver(sourceCredentialsInputSchema),
    defaultValues: { values: { ...credentials.public_values }, expires_on: '' },
  });

  const onSubmit = handleSubmit(({ values, expires_on }) => {
    configuration.mutate(
      { adapter: credentials.adapter, values, expires_on },
      {
        onSuccess: onSaved,
        onError: (error) => {
          fields
            .filter((field) => field.secret)
            .forEach((field) => resetField(`values.${field.name}`));
          showRefusal(error, setError, (field) =>
            declaredFieldOf(fields, field) === undefined ? undefined : `values.${field}`,
          );
        },
        onSettled: () => configuration.reset(),
      },
    );
  });

  return (
    <form
      aria-label={`Credenziali di ${credentials.adapter}`}
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="mt-2 space-y-3"
    >
      <FormAlert error={errors.root?.server} />
      <DeclaredFields
        fields={fields}
        registerField={(name) => register(`values.${name}`)}
        reasonOf={(name) => errors.values?.[name]?.message}
      />
      {credentials.expiry_editable && (
        <InputField
          label="Scadenza"
          type="date"
          error={errors.expires_on}
          {...register('expires_on')}
        />
      )}
      <div className="flex flex-wrap gap-2">
        <CommandButton tone="primary" type="submit" disabled={configuration.isPending}>
          Salva le credenziali
        </CommandButton>
        <CommandButton tone="secondary" onClick={onCancel}>
          Annulla
        </CommandButton>
      </div>
    </form>
  );
};
