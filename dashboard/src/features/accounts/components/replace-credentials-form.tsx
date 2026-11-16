import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert } from '@/components/ui/form/input-field';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import {
  credentialsInputSchema,
  useReplaceCredentials,
  type CredentialsInput,
} from '../api/replace-credentials';

import { PublicFields } from './public-fields';

const EMPTY_FORM: CredentialsInput = { credentials: {} };

type ReplaceCredentialsFormProps = {
  readonly account: Account;
  readonly onReplaced: () => void;
  readonly onCancel: () => void;
};

/**
 * New credentials for an account, with the fields its exchange declares (R2.3.9), checked with the exchange before
 * they take the place of the old ones (R0.2.4). The public fields the account keeps are shown and not asked: only an
 * account registered before they were kept asks them all (Bug 401).
 */
export const ReplaceCredentialsForm = ({
  account,
  onReplaced,
  onCancel,
}: ReplaceCredentialsFormProps) => {
  const replacement = useReplaceCredentials();
  const exchanges = useSupportedExchanges();
  const declared =
    exchanges.data?.find((exchange) => exchange.name === account.exchange)?.fields ?? [];
  const fields = declared.filter((field) => field.secret || !(field.name in account.public_fields));
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

  const onSubmit = handleSubmit(({ credentials }) => {
    replacement.mutate(
      { accountId: account.id, credentials },
      {
        onSuccess: onReplaced,
        onError: (error) => {
          fields
            .filter((field) => field.secret)
            .forEach((field) => resetField(`credentials.${field.name}`));
          showRefusal(error, setError, (field) =>
            declaredFieldOf(fields, field) === undefined ? undefined : `credentials.${field}`,
          );
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
      <PublicFields fields={declared} values={account.public_fields} />
      <DeclaredFields
        fields={fields}
        registerField={(name) => register(`credentials.${name}`)}
        reasonOf={(name) => errors.credentials?.[name]?.message}
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={replacement.isPending || !exchanges.isSuccess}
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
