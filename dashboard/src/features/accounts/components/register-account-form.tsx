import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { SelectField } from '@/components/ui/form/select-field';
import { isRealMoney, RealMoneyNotice } from '@/components/ui/real-money';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { showRefusal } from '@/lib/form-errors';

import {
  accountRegistrationInputSchema,
  useRegisterAccount,
  type AccountRegistrationInput,
} from '../api/register-account';

const FIELDS = ['name', 'exchange'] as const;

const EMPTY_FORM: AccountRegistrationInput = { name: '', exchange: '', credentials: {} };

/**
 * Registers an account on an exchange the API supports (R2.3.8), asking the data that exchange declares (R2.3.9): the
 * API checks the credentials with the exchange before saving them (R0.2.1), and the form warns when the chosen
 * exchange trades real money (ADR 0157).
 */
export const RegisterAccountForm = () => {
  const registration = useRegisterAccount();
  // Without the list of the supported exchanges the user cannot choose one: the form waits for it (ADR 0153).
  const exchanges = useSupportedExchanges();
  const [registered, setRegistered] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    reset,
    resetField,
    setError,
    formState: { errors },
  } = useForm<AccountRegistrationInput>({
    resolver: zodResolver(accountRegistrationInputSchema),
    defaultValues: EMPTY_FORM,
    // The fields of another exchange leave the values with their inputs: only those of the chosen one are sent.
    shouldUnregister: true,
  });
  const chosenExchange = useWatch({ control, name: 'exchange' });
  const exchange = exchanges.data?.find((supported) => supported.name === chosenExchange);
  const fields = exchange?.fields ?? [];

  const onSubmit = handleSubmit((input) => {
    setRegistered(null);
    registration.mutate(input, {
      onSuccess: (account) => {
        reset(EMPTY_FORM);
        setRegistered(account.name);
      },
      onError: (error) => {
        fields
          .filter((field) => field.secret)
          .forEach((field) => resetField(`credentials.${field.name}`));
        showRefusal(error, setError, (field) =>
          declaredFieldOf(fields, field) === undefined
            ? FIELDS.find((known) => known === field)
            : `credentials.${field}`,
        );
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
          choices={(exchanges.data ?? []).map(({ name }) => ({ value: name, label: name }))}
          loading={exchanges.isPending}
          unavailable={
            exchanges.isError
              ? { prefix: 'Impossibile leggere gli exchange supportati', error: exchanges.error }
              : undefined
          }
          error={errors.exchange}
          {...register('exchange')}
        />
        {isRealMoney(exchange?.network) && <RealMoneyNotice subject="Il conto" />}
        <DeclaredFields
          fields={fields}
          registerField={(name) => register(`credentials.${name}`)}
          reasonOf={(name) => errors.credentials?.[name]?.message}
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
