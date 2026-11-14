import { zodResolver } from '@hookform/resolvers/zod';
import { FormProvider, useForm } from 'react-hook-form';

import { FormField } from '@/components/ui/form/form-field';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import type { Model } from '../api/get-model-catalog';
import type { Source } from '../api/get-sources';
import { flowFormSchema, formFieldOf, type FlowFormValues } from '../utils/flow-form';

import { ModelFields } from './model-fields';
import { SourceFields } from './source-fields';

const INPUT = 'rounded border border-slate-300 px-2 py-1';

type FlowFormProps = {
  readonly values: FlowFormValues;
  readonly accounts: Account[];
  readonly models: Model[];
  readonly sources: Source[];
  readonly submitLabel: string;
  /** Whether the name is fixed: the API changes every setting of a flow but its name (R1.1.3). */
  readonly nameFixed?: boolean;
  readonly onSave: (values: FlowFormValues) => Promise<unknown>;
};

/**
 * The whole configuration of a flow in one form (ADR 0131): the choices of sources and models come from the catalogs,
 * and every reason of a refusal shows beside the field it concerns (R2.3.3).
 */
export const FlowForm = ({
  values,
  accounts,
  models,
  sources,
  submitLabel,
  nameFixed = false,
  onSave,
}: FlowFormProps) => {
  const form = useForm<FlowFormValues>({ resolver: zodResolver(flowFormSchema), values });
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = form;

  const save = handleSubmit(async (submitted) => {
    try {
      await onSave(submitted);
    } catch (error) {
      showRefusal(error, setError, formFieldOf);
    }
  });

  return (
    <FormProvider {...form}>
      <form
        aria-label="Configurazione del flusso"
        noValidate
        onSubmit={(event) => void save(event)}
        className="space-y-4 rounded border border-slate-200 bg-white p-4"
      >
        {errors.root?.server?.message !== undefined && (
          <p role="alert" className="text-red-700">
            {errors.root.server.message}
          </p>
        )}
        <FormField id="flow-name" label="Nome" error={errors.name?.message}>
          {(control) => (
            <input {...control} {...register('name')} readOnly={nameFixed} className={INPUT} />
          )}
        </FormField>
        <FormField id="flow-account" label="Conto" error={errors.account_id?.message}>
          {(control) => (
            <select {...control} {...register('account_id')} className={INPUT}>
              <option value="">Scegli un conto</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          )}
        </FormField>
        <FormField id="flow-assets" label="Asset" error={errors.assets?.message}>
          {(control) => (
            <input {...control} {...register('assets')} placeholder="BTC, ETH" className={INPUT} />
          )}
        </FormField>
        <FormField
          id="flow-cycle-minutes"
          label="Intervallo del ciclo in minuti"
          error={errors.cycle_minutes?.message}
        >
          {(control) => (
            <input
              {...control}
              {...register('cycle_minutes')}
              inputMode="numeric"
              className={INPUT}
            />
          )}
        </FormField>
        <SourceFields sources={sources} />
        <ModelFields models={models} />
        <FormField id="flow-instructions" label="Istruzioni" error={errors.instructions?.message}>
          {(control) => (
            <textarea {...control} {...register('instructions')} rows={4} className={INPUT} />
          )}
        </FormField>
        <fieldset className="space-y-2">
          <legend className="font-semibold">Rischio</legend>
          <FormField
            id="flow-max-leverage"
            label="Leva massima"
            error={errors.max_leverage?.message}
          >
            {(control) => (
              <input
                {...control}
                {...register('max_leverage')}
                inputMode="numeric"
                className={INPUT}
              />
            )}
          </FormField>
          <FormField
            id="flow-max-margin-exposure"
            label="Esposizione massima del margine (%)"
            error={errors.max_margin_exposure_percent?.message}
          >
            {(control) => (
              <input
                {...control}
                {...register('max_margin_exposure_percent')}
                inputMode="decimal"
                className={INPUT}
              />
            )}
          </FormField>
          <FormField
            id="flow-max-value-exposure"
            label="Esposizione massima del valore (%)"
            error={errors.max_value_exposure_percent?.message}
          >
            {(control) => (
              <input
                {...control}
                {...register('max_value_exposure_percent')}
                inputMode="decimal"
                className={INPUT}
              />
            )}
          </FormField>
        </fieldset>
        <FormField
          id="flow-allocated-capital"
          label="Capitale allocato"
          error={errors.allocated_capital?.message}
        >
          {(control) => (
            <input
              {...control}
              {...register('allocated_capital')}
              inputMode="decimal"
              className={INPUT}
            />
          )}
        </FormField>
        <label className="flex items-center gap-2">
          <input type="checkbox" {...register('bring_to_minimum')} />
          Porta le aperture al minimo dell&apos;exchange
        </label>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          {submitLabel}
        </button>
      </form>
    </FormProvider>
  );
};
