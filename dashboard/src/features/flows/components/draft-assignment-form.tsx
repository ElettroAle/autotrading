import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';

import { AssetPicker } from '@/components/ui/form/asset-picker';
import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';
import { useTradableAssets } from '@/hooks/use-tradable-assets';
import { showRefusal } from '@/lib/form-errors';

import {
  assignmentInputSchema,
  useAssignDraftFlow,
  type AssignmentInput,
} from '../api/assign-draft-flow';
import type { Account } from '../api/get-accounts';

import { CommandRefusal } from './command-refusal';

// The names the API gives to the fields of the request, as its invalid requests report them.
const FIELDS_OF_REQUEST: Record<string, keyof AssignmentInput> = {
  account_id: 'accountId',
  allocated_capital: 'allocatedCapital',
  assets: 'assets',
};

/** Account, capital and assets of a draft, sent to the API; its refusals stay beside the fields (ADR 0125). */
export const DraftAssignmentForm = ({
  flowId,
  accounts,
}: {
  flowId: string;
  accounts: Account[];
}) => {
  const assign = useAssignDraftFlow(flowId);
  // Without the list of the tradable assets the user cannot choose them: the form waits for it (ADR 0147).
  const tradable = useTradableAssets();
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<AssignmentInput>({
    resolver: zodResolver(assignmentInputSchema),
    defaultValues: { accountId: '', allocatedCapital: '', assets: [] },
  });

  useEffect(() => {
    if (assign.error !== null) {
      showRefusal(assign.error, setError, (field) => FIELDS_OF_REQUEST[field]);
    }
  }, [assign.error, setError]);

  return (
    <form
      aria-label="Assegnazione della bozza"
      noValidate
      onSubmit={handleSubmit((input) => assign.mutate(input))}
      className="mt-4 flex flex-col gap-3 rounded border border-slate-200 p-3"
    >
      <FormField id="assignment-account" label="Conto" error={errors.accountId?.message}>
        {(control) => (
          <select {...control} className={FORM_CONTROL} {...register('accountId')}>
            <option value="">Scegli un conto</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        )}
      </FormField>
      <FormField
        id="assignment-capital"
        label="Capitale allocato (USDC)"
        error={errors.allocatedCapital?.message}
      >
        {(control) => (
          <input
            {...control}
            inputMode="decimal"
            className={FORM_CONTROL}
            {...register('allocatedCapital')}
          />
        )}
      </FormField>
      <Controller
        control={control}
        name="assets"
        render={({ field }) => (
          <AssetPicker
            id="assignment-assets"
            chosen={field.value}
            onChange={field.onChange}
            onBlur={field.onBlur}
            inputRef={field.ref}
            error={errors.assets?.message}
          />
        )}
      />
      <button
        type="submit"
        disabled={assign.isPending || !tradable.isSuccess}
        className="self-start rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
      >
        Assegna
      </button>
      <CommandRefusal refusal="Assegnazione rifiutata" error={assign.error} />
    </form>
  );
};
