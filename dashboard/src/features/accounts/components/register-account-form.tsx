import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

import { Card } from '@/components/ui/card';
import { CommandButton } from '@/components/ui/command-button';
import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { SelectField } from '@/components/ui/form/select-field';
import { EXPIRY_INFO } from '@/components/ui/key-expiry';
import { NetworkNotice } from '@/components/ui/network-notice';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { showRefusal } from '@/lib/form-errors';

import {
  accountRegistrationInputSchema,
  useRegisterAccount,
  type AccountRegistrationInput,
} from '../api/register-account';
import { ACCOUNT_SETTING_INFO, credentialInfoOf } from '../utils/setting-info';

const FIELDS = ['name', 'exchange', 'expires_on', 'virtual_balance'] as const;

const EMPTY_FORM: AccountRegistrationInput = {
  name: '',
  exchange: '',
  credentials: {},
  expires_on: '',
  virtual_balance: '',
};

/**
 * Registers an account on an exchange the API supports (R2.3.8), asking the data that exchange declares (R2.3.9): the
 * API checks the credentials with the exchange before saving them (R0.2.1), and the form warns when the chosen
 * exchange trades real money (ADR 0157). An exchange that holds a virtual balance asks it instead (R6.3.2).
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
    <Card as="section" aria-labelledby="register-account-title">
      <h2 id="register-account-title" className="mb-2 text-xl font-semibold">
        Nuovo conto
      </h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <FormAlert error={errors.root?.server} />
        <InputField
          label="Nome"
          info={ACCOUNT_SETTING_INFO.name}
          error={errors.name}
          {...register('name')}
        />
        <SelectField
          label="Exchange"
          info={ACCOUNT_SETTING_INFO.exchange}
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
        {exchange && (
          <NetworkNotice
            subject="Il conto"
            network={exchange.network}
            networkName={exchange.network_name}
          />
        )}
        <DeclaredFields
          fields={fields}
          infoOf={credentialInfoOf}
          registerField={(name) => register(`credentials.${name}`)}
          reasonOf={(name) => errors.credentials?.[name]?.message}
        />
        {/* Only where the exchange holds a virtual balance, as the API says (R6.3.2). */}
        {exchange?.virtual_balance === true && (
          <InputField
            label="Saldo virtuale"
            info={ACCOUNT_SETTING_INFO.virtualBalance}
            inputMode="decimal"
            error={errors.virtual_balance}
            {...register('virtual_balance')}
          />
        )}
        {/* Only where the exchange does not read the expiry of the credentials, as the API says (R6.2.2). */}
        {exchange?.expiry_editable === true && (
          <InputField
            label="Scadenza"
            info={EXPIRY_INFO}
            type="date"
            error={errors.expires_on}
            {...register('expires_on')}
          />
        )}
        <CommandButton
          tone="primary"
          type="submit"
          disabled={registration.isPending || !exchanges.isSuccess}
        >
          Registra il conto
        </CommandButton>
        {registered !== null && (
          <p role="status" className="text-green-800">
            Conto {registered} registrato
          </p>
        )}
      </form>
    </Card>
  );
};
