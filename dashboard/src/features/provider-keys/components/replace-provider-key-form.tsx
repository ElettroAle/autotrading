import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { DeclaredFields, declaredFieldOf } from '@/components/ui/form/declared-fields';
import { FormAlert } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import { useModelProviders } from '../api/get-model-providers';
import type { ProviderKey } from '../api/get-provider-keys';
import {
  newKeyInputSchema,
  useReplaceProviderKey,
  type NewKeyInput,
} from '../api/replace-provider-key';

type ReplaceProviderKeyFormProps = {
  readonly providerKey: ProviderKey;
  readonly onReplaced: () => void;
  readonly onCancel: () => void;
};

/** A new key for the provider, with the fields it declares (R2.3.9): the next cycles of the flows use it (R1.4.1). */
export const ReplaceProviderKeyForm = ({
  providerKey,
  onReplaced,
  onCancel,
}: ReplaceProviderKeyFormProps) => {
  const replacement = useReplaceProviderKey();
  const providers = useModelProviders();
  const fields =
    providers.data?.find((provider) => provider.name === providerKey.provider)?.key_fields ?? [];
  const {
    register,
    handleSubmit,
    resetField,
    setError,
    formState: { errors },
  } = useForm<NewKeyInput>({
    resolver: zodResolver(newKeyInputSchema),
    defaultValues: { key: {} },
  });

  const onSubmit = handleSubmit(({ key }) => {
    replacement.mutate(
      { provider: providerKey.provider, key },
      {
        onSuccess: onReplaced,
        onError: (error) => {
          fields
            .filter((field) => field.secret)
            .forEach((field) => resetField(`key.${field.name}`));
          showRefusal(error, setError, (field) =>
            declaredFieldOf(fields, field) === undefined ? undefined : `key.${field}`,
          );
        },
        onSettled: () => replacement.reset(),
      },
    );
  });

  return (
    <form
      aria-label={`Nuova chiave di ${providerKey.provider}`}
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="mt-2 space-y-3"
    >
      <FormAlert error={errors.root?.server} />
      <DeclaredFields
        fields={fields}
        registerField={(name) => register(`key.${name}`)}
        reasonOf={(name) => errors.key?.[name]?.message}
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={replacement.isPending || !providers.isSuccess}
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
