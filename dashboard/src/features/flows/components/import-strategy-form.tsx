import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router';

import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';
import { paths } from '@/config/paths';

import {
  importInputSchema,
  useImportFlowStrategy,
  type ImportInput,
} from '../api/import-flow-strategy';

import { CommandRefusal } from './command-refusal';

/** A strategy file becomes a new draft, opened for the assignment of account, capital and assets (ADR 0141). */
export const ImportStrategyForm = () => {
  const navigate = useNavigate();
  const importStrategy = useImportFlowStrategy({
    onSuccess: (draft) => {
      void navigate(paths.flow.getHref(draft.id));
    },
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ImportInput>({
    resolver: zodResolver(importInputSchema),
    defaultValues: { name: '' },
  });

  return (
    <form
      aria-label="Importazione di una strategia"
      noValidate
      onSubmit={handleSubmit((input) => importStrategy.mutate(input))}
      className="mt-6 flex flex-col gap-3 rounded border border-slate-200 bg-white p-3"
    >
      <h2 className="font-semibold">Importa una strategia</h2>
      <FormField id="import-name" label="Nome del nuovo flusso" error={errors.name?.message}>
        {(control) => <input {...control} className={FORM_CONTROL} {...register('name')} />}
      </FormField>
      <FormField id="import-file" label="File della strategia" error={errors.files?.message}>
        {(control) => (
          <input
            {...control}
            type="file"
            accept="application/json,.json"
            className={FORM_CONTROL}
            {...register('files')}
          />
        )}
      </FormField>
      <button
        type="submit"
        disabled={importStrategy.isPending}
        className="self-start rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
      >
        Importa
      </button>
      <CommandRefusal refusal="Importazione rifiutata" error={importStrategy.error} />
    </form>
  );
};
