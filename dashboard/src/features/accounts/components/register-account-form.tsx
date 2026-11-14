import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { FormAlert, InputField, SecretField } from '@/components/ui/form/input-field';
import { SelectField } from '@/components/ui/form/select-field';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { showRefusal } from '@/lib/form-errors';

import {
  accountRegistrationInputSchema,
  useRegisterAccount,
  type AccountRegistrationInput,
} from '../api/register-account';

const FIELDS = ['name', 'exchange', 'account_address', 'secret_key'] as const;

const EMPTY_FORM: AccountRegistrationInput = {
  name: '',
  exchange: '',
  account_address: '',
  secret_key: '',
};

/**
 * Registers an account on an exchange the API supports (R2.3.8): the API checks the credentials with the exchange
 * before saving them (R0.2.1).
 */
export const RegisterAccountForm = () => {
  const registration = useRegisterAccount();
  // Without the list of the supported exchanges the user cannot choose one: the form waits for it (ADR 0153).
  const exchanges = useSupportedExchanges();
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
        <SelectField
          label="Exchange"
          placeholder="Scegli un exchange"
          choices={(exchanges.data ?? []).map((name) => ({ value: name, label: name }))}
          loading={exchanges.isPending}
          unavailable={
            exchanges.isError
              ? { prefix: 'Impossibile leggere gli exchange supportati', error: exchanges.error }
              : undefined
          }
          error={errors.exchange}
          {...register('exchange')}
        />
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
          disabled={registration.isPending || !exchanges.isSuccess}
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
