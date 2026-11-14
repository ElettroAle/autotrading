import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { FormAlert, SecretField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import type { ProviderKey } from '../api/get-provider-keys';
import {
  newKeyInputSchema,
  useReplaceProviderKey,
  type NewKeyInput,
} from '../api/replace-provider-key';

const FIELDS = ['key'] as const;

type ReplaceProviderKeyFormProps = {
  readonly providerKey: ProviderKey;
  readonly onReplaced: () => void;
  readonly onCancel: () => void;
};

/** A new key for the provider: the next cycles of the flows use it (R1.4.1). */
export const ReplaceProviderKeyForm = ({
  providerKey,
  onReplaced,
  onCancel,
}: ReplaceProviderKeyFormProps) => {
  const replacement = useReplaceProviderKey();
  const {
    register,
    handleSubmit,
    resetField,
    setError,
    formState: { errors },
  } = useForm<NewKeyInput>({
    resolver: zodResolver(newKeyInputSchema),
    defaultValues: { key: '' },
  });

  const onSubmit = handleSubmit(({ key }) => {
    replacement.mutate(
      { provider: providerKey.provider, key },
      {
        onSuccess: onReplaced,
        onError: (error) => {
          resetField('key');
          showRefusal(error, setError, (field) => FIELDS.find((known) => known === field));
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
      <SecretField label="Nuova chiave" error={errors.key} {...register('key')} />
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
