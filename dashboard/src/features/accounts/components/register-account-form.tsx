import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { FormAlert, InputField, SecretField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import {
  accountRegistrationInputSchema,
  useRegisterAccount,
  type AccountRegistrationInput,
} from '../api/register-account';

const FIELDS = ['name', 'exchange', 'account_address', 'secret_key'] as const;

// The exchange the platform integrates today, offered as a start: the API tells which ones it accepts (R0.2.1).
const EMPTY_FORM: AccountRegistrationInput = {
  name: '',
  exchange: 'hyperliquid',
  account_address: '',
  secret_key: '',
};

/** Registers an account: the API checks the credentials with the exchange before saving them (R0.2.1). */
export const RegisterAccountForm = () => {
  const registration = useRegisterAccount();
  const [registered, setRegistered] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    resetField,
    setError,
    formState: { errors },
  } = useForm<AccountRegistrationInput>({
    resolver: zodResolver(accountRegistrationInputSchema),
    defaultValues: EMPTY_FORM,
  });

  const onSubmit = handleSubmit((input) => {
    setRegistered(null);
    registration.mutate(input, {
      onSuccess: (account) => {
        reset(EMPTY_FORM);
        setRegistered(account.name);
      },
      onError: (error) => {
        resetField('secret_key');
        showRefusal(error, setError, (field) => FIELDS.find((known) => known === field));
      },
      onSettled: () => registration.reset(),
    });
  });

  return (
    <section
      aria-labelledby="register-account-title"
      className="rounded border border-slate-200 bg-white p-4"
    >
      <h2 id="register-account-title" className="mb-2 text-xl font-semibold">
        Nuovo conto
      </h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <FormAlert error={errors.root?.server} />
        <InputField label="Nome" error={errors.name} {...register('name')} />
        <InputField label="Exchange" error={errors.exchange} {...register('exchange')} />
        <InputField
          label="Indirizzo del conto"
          error={errors.account_address}
          {...register('account_address')}
        />
        <SecretField
          label="Chiave dell'API wallet"
          error={errors.secret_key}
          {...register('secret_key')}
        />
        <button
          type="submit"
          disabled={registration.isPending}
          className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Registra il conto
        </button>
        {registered !== null && (
          <p role="status" className="text-green-800">
            Conto {registered} registrato
          </p>
        )}
      </form>
    </section>
  );
};
