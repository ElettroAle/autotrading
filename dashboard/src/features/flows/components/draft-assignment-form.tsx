import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm, type UseFormSetError } from 'react-hook-form';

import { FORM_CONTROL, FormField } from '@/components/ui/form-field';
import { ApiError } from '@/lib/api-client';

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

const showFieldErrors = (error: Error | null, setError: UseFormSetError<AssignmentInput>) => {
  if (!(error instanceof ApiError)) {
    return;
  }
  for (const [name, message] of Object.entries(error.fieldErrors)) {
    const field = FIELDS_OF_REQUEST[name];
    if (field !== undefined) {
      setError(field, { message });
    }
  }
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
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<AssignmentInput>({
    resolver: zodResolver(assignmentInputSchema),
    defaultValues: { accountId: '', allocatedCapital: '', assets: '' },
  });

  useEffect(() => showFieldErrors(assign.error, setError), [assign.error, setError]);

  return (
    <form
      aria-label="Assegnazione della bozza"
      noValidate
      onSubmit={handleSubmit((input) => assign.mutate(input))}
      className="mt-4 flex flex-col gap-3 rounded border border-slate-200 p-3"
    >
      <FormField id="assignment-account" label="Conto" error={errors.accountId?.message}>
        <select id="assignment-account" className={FORM_CONTROL} {...register('accountId')}>
          <option value="">Scegli un conto</option>
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
      </FormField>
      <FormField
        id="assignment-capital"
        label="Capitale allocato (USDC)"
        error={errors.allocatedCapital?.message}
      >
        <input
          id="assignment-capital"
          inputMode="decimal"
          className={FORM_CONTROL}
          {...register('allocatedCapital')}
        />
      </FormField>
      <FormField id="assignment-assets" label="Asset" error={errors.assets?.message}>
        <input
          id="assignment-assets"
          placeholder="BTC, ETH"
          className={FORM_CONTROL}
          {...register('assets')}
        />
      </FormField>
      <button
        type="submit"
        disabled={assign.isPending}
        className="self-start rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
      >
        Assegna
      </button>
      <CommandRefusal refusal="Assegnazione rifiutata" error={assign.error} />
    </form>
  );
};
