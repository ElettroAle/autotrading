import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { FormAlert, InputField, SecretField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import {
  credentialsInputSchema,
  useReplaceCredentials,
  type CredentialsInput,
} from '../api/replace-credentials';

const FIELDS = ['account_address', 'secret_key'] as const;

const EMPTY_FORM: CredentialsInput = { account_address: '', secret_key: '' };

type ReplaceCredentialsFormProps = {
  readonly account: Account;
  readonly onReplaced: () => void;
  readonly onCancel: () => void;
};

/** New credentials for an account, checked with the exchange before they take the place of the old ones (R0.2.4). */
export const ReplaceCredentialsForm = ({
  account,
  onReplaced,
  onCancel,
}: ReplaceCredentialsFormProps) => {
  const replacement = useReplaceCredentials();
  const {
    register,
    handleSubmit,
    resetField,
    setError,
    formState: { errors },
  } = useForm<CredentialsInput>({
    resolver: zodResolver(credentialsInputSchema),
    defaultValues: EMPTY_FORM,
  });

  const onSubmit = handleSubmit((credentials) => {
    replacement.mutate(
      { accountId: account.id, credentials },
      {
        onSuccess: onReplaced,
        onError: (error) => {
          resetField('secret_key');
          showRefusal(error, setError, (field) => FIELDS.find((known) => known === field));
        },
        onSettled: () => replacement.reset(),
      },
    );
  });

  return (
    <form
      aria-label={`Nuove credenziali del conto ${account.name}`}
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="mt-2 space-y-3"
    >
      <FormAlert error={errors.root?.server} />
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
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={replacement.isPending}
          className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Sostituisci
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-slate-300 px-3 py-1.5"
        >
          Annulla
        </button>
      </div>
    </form>
  );
};
