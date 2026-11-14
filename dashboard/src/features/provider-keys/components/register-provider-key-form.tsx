import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { FormAlert, InputField, SecretField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import {
  providerKeyInputSchema,
  useRegisterProviderKey,
  type ProviderKeyInput,
} from '../api/register-provider-key';

const FIELDS = ['provider', 'key'] as const;

const EMPTY_FORM: ProviderKeyInput = { provider: '', key: '' };

/** Registers the key of a provider of models, without asking the provider about it (R1.4.1). */
export const RegisterProviderKeyForm = () => {
  const registration = useRegisterProviderKey();
  const [registered, setRegistered] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    resetField,
    setError,
    formState: { errors },
  } = useForm<ProviderKeyInput>({
    resolver: zodResolver(providerKeyInputSchema),
    defaultValues: EMPTY_FORM,
  });

  const onSubmit = handleSubmit((input) => {
    setRegistered(null);
    registration.mutate(input, {
      onSuccess: (key) => {
        reset(EMPTY_FORM);
        setRegistered(key.provider);
      },
      onError: (error) => {
        resetField('key');
        showRefusal(error, setError, (field) => FIELDS.find((known) => known === field));
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
        <InputField label="Fornitore" error={errors.provider} {...register('provider')} />
        <SecretField label="Chiave" error={errors.key} {...register('key')} />
        <button
          type="submit"
          disabled={registration.isPending}
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
