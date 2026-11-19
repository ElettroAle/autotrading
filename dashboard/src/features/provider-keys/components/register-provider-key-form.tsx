import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { SelectField, type SelectOption } from '@/components/ui/form/select-field';
import { showRefusal } from '@/lib/form-errors';

import { useModelProviders, type ModelProvider } from '../api/get-model-providers';
import {
  providerKeyInputSchema,
  useRegisterProviderKey,
  type ProviderKeyInput,
} from '../api/register-provider-key';

const FIELDS = ['provider', 'expires_on'] as const;

const EMPTY_FORM: ProviderKeyInput = { provider: '', key: {}, expires_on: '' };

// A provider whose key is registered is not chosen here: its key is replaced from the list (R2.3.2).
const optionOf = ({ name, key_registered }: ModelProvider): SelectOption =>
  key_registered
    ? { value: name, label: name, disabled: true, note: 'chiave già registrata' }
    : { value: name, label: name };

/**
 * Registers the key of a provider of the catalog of the models (R2.3.8), with the fields that provider declares
 * (R2.3.9), without asking the provider about it (R1.4.1).
 */
export const RegisterProviderKeyForm = () => {
  const registration = useRegisterProviderKey();
  // Without the providers of the catalog the user cannot choose one: the form waits for them (ADR 0153).
  const providers = useModelProviders();
  const [registered, setRegistered] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    reset,
    resetField,
    setError,
    formState: { errors },
  } = useForm<ProviderKeyInput>({
    resolver: zodResolver(providerKeyInputSchema),
    defaultValues: EMPTY_FORM,
    // The fields of another provider leave the values with their inputs: only those of the chosen one are sent.
    shouldUnregister: true,
  });
  const chosenProvider = useWatch({ control, name: 'provider' });
  const chosen = providers.data?.find((provider) => provider.name === chosenProvider);
  const fields = chosen?.key_fields ?? [];

  const onSubmit = handleSubmit((input) => {
    setRegistered(null);
    registration.mutate(input, {
      onSuccess: (key) => {
        reset(EMPTY_FORM);
        setRegistered(key.provider);
      },
      onError: (error) => {
        fields.filter((field) => field.secret).forEach((field) => resetField(`key.${field.name}`));
        showRefusal(error, setError, (field) =>
          declaredFieldOf(fields, field) === undefined
            ? FIELDS.find((known) => known === field)
            : `key.${field}`,
        );
      },
      onSettled: () => registration.reset(),
    });
  });

  return (
    <section
      aria-labelledby="register-provider-key-title"
      className="rounded border border-slate-200 bg-white p-4"
    >
      <h2 id="register-provider-key-title" className="mb-2 text-xl font-semibold">
        Nuova chiave
      </h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <FormAlert error={errors.root?.server} />
        <SelectField
          label="Fornitore"
          placeholder="Scegli un fornitore"
          choices={(providers.data ?? []).map(optionOf)}
          loading={providers.isPending}
          unavailable={
            providers.isError
              ? { prefix: 'Impossibile leggere i fornitori IA', error: providers.error }
              : undefined
          }
          error={errors.provider}
          {...register('provider')}
        />
        <DeclaredFields
          fields={fields}
          registerField={(name) => register(`key.${name}`)}
          reasonOf={(name) => errors.key?.[name]?.message}
        />
        {/* Only where no gateway reads the expiry of the keys of the provider, as the API says (R6.2.2). */}
        {chosen?.expiry_editable === true && (
          <InputField
            label="Scadenza"
            type="date"
            error={errors.expires_on}
            {...register('expires_on')}
          />
        )}
        <button
          type="submit"
          disabled={registration.isPending || !providers.isSuccess}
          className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Registra la chiave
        </button>
        {registered !== null && (
          <p role="status" className="text-green-800">
            Chiave di {registered} registrata
          </p>
        )}
      </form>
    </section>
  );
};
