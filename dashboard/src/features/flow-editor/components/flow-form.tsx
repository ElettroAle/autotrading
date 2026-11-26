import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, FormProvider, useForm } from 'react-hook-form';

import { Card } from '@/components/ui/card';
import { AssetPicker } from '@/components/ui/form/asset-picker';
import { FORM_CONTROL, FORM_TEXT_AREA, FormField } from '@/components/ui/form/form-field';
import { InputField } from '@/components/ui/form/input-field';
import { SelectField, type SelectOption } from '@/components/ui/form/select-field';
import { useTradableAssets } from '@/hooks/use-tradable-assets';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import type { Model, Provider } from '../api/get-model-catalog';
import type { Source } from '../api/get-sources';
import type { DefaultSystemPrompt } from '../api/get-system-prompt';
import { flowFormSchema, formFieldOf, type FlowFormValues } from '../utils/flow-form';

import { AccountExposureField } from './account-exposure-field';
import { ConsecutiveLossFields } from './consecutive-loss-fields';
import { MemoryFields } from './memory-fields';
import { ModelFields } from './model-fields';
import { SourceFields } from './source-fields';
import { SystemPromptField } from './system-prompt-field';
import { TrailingStopFields } from './trailing-stop-fields';

// How suspended openings resume: by the user, or on their own at the next midnight UTC (R3.2.2).
const OPENINGS_RESUME_CHOICES: readonly SelectOption[] = [
  { value: 'manual', label: 'manuale' },
  { value: 'next_day', label: 'il giorno dopo' },
];

type FlowFormProps = {
  readonly values: FlowFormValues;
  readonly accounts: Account[];
  readonly models: Model[];
  readonly providers: Provider[];
  readonly sources: Source[];
  readonly systemPrompt: DefaultSystemPrompt;
  readonly submitLabel: string;
  /** Whether the account is chosen: at creation and on a draft; any other flow keeps its own (ADR
   * assegnazione-della-bozza-nel-form-di-configurazione). */
  readonly accountChosen?: boolean;
  readonly onSave: (values: FlowFormValues) => Promise<unknown>;
};

/** The account of the flow, read and not chosen, by its name when the accounts are read (R1.1.1). */
const FixedAccount = ({ accountId, accounts }: { accountId: string; accounts: Account[] }) => (
  <FormField id="flow-account" label="Conto" error={undefined}>
    {(control) => (
      <input
        {...control}
        readOnly
        value={accounts.find((account) => account.id === accountId)?.name ?? accountId}
        className={FORM_CONTROL}
      />
    )}
  </FormField>
);

/**
 * The whole configuration of a flow in one form (ADR 0131): the choices of sources and models come from the catalogs,
 * and every reason of a refusal shows beside the field it concerns (R2.3.3).
 */
export const FlowForm = ({
  values,
  accounts,
  models,
  providers,
  sources,
  systemPrompt,
  submitLabel,
  accountChosen = true,
  onSave,
}: FlowFormProps) => {
  const form = useForm<FlowFormValues>({ resolver: zodResolver(flowFormSchema), values });
  // Without the list of the tradable assets the user cannot choose them: the form waits for it (ADR 0147).
  const tradable = useTradableAssets();
  const {
    register,
    control,
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
      <Card className="min-w-0">
        <form
          aria-label="Configurazione del flusso"
          noValidate
          onSubmit={(event) => void save(event)}
          className="space-y-4"
        >
          {errors.root?.server?.message !== undefined && (
            <p role="alert" className="text-red-700">
              {errors.root.server.message}
            </p>
          )}
          <FormField id="flow-name" label="Nome" error={errors.name?.message}>
            {(control) => <input {...control} {...register('name')} className={FORM_CONTROL} />}
          </FormField>
          {accountChosen ? (
            <FormField id="flow-account" label="Conto" error={errors.account_id?.message}>
              {(control) => (
                <select {...control} {...register('account_id')} className={FORM_CONTROL}>
                  <option value="">Scegli un conto</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
          ) : (
            <FixedAccount accountId={values.account_id} accounts={accounts} />
          )}
          <Controller
            control={control}
            name="assets"
            render={({ field }) => (
              <AssetPicker
                id="flow-assets"
                chosen={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                inputRef={field.ref}
                error={errors.assets?.message}
              />
            )}
          />
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
                className={FORM_CONTROL}
              />
            )}
          </FormField>
          <SourceFields sources={sources} />
          <ModelFields models={models} providers={providers} currentModel={values.model} />
          <MemoryFields />
          <AccountExposureField />
          <FormField id="flow-instructions" label="Istruzioni" error={errors.instructions?.message}>
            {(control) => (
              <textarea
                {...control}
                {...register('instructions')}
                rows={4}
                className={FORM_TEXT_AREA}
              />
            )}
          </FormField>
          <SystemPromptField systemPrompt={systemPrompt} />
          <fieldset className="min-w-0 space-y-2">
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
                  className={FORM_CONTROL}
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
                  className={FORM_CONTROL}
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
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <FormField
              id="flow-max-total-margin-exposure"
              label="Esposizione complessiva massima del margine (%)"
              error={errors.max_total_margin_exposure_percent?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('max_total_margin_exposure_percent')}
                  inputMode="decimal"
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <FormField
              id="flow-max-total-value-exposure"
              label="Esposizione complessiva massima del valore (%)"
              error={errors.max_total_value_exposure_percent?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('max_total_value_exposure_percent')}
                  inputMode="decimal"
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <FormField
              id="flow-max-consecutive-failures"
              label="Massimo di cicli falliti consecutivi"
              error={errors.max_consecutive_failures?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('max_consecutive_failures')}
                  inputMode="numeric"
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <InputField
              id="flow-max-daily-loss"
              label="Perdita giornaliera massima (%)"
              error={errors.max_daily_loss_percent}
              inputMode="decimal"
              {...register('max_daily_loss_percent')}
            />
            <InputField
              id="flow-max-drawdown"
              label="Perdita massima dal picco (%)"
              error={errors.max_drawdown_percent}
              inputMode="decimal"
              {...register('max_drawdown_percent')}
            />
            <SelectField
              id="flow-openings-resume"
              label="Ripresa delle aperture"
              placeholder="Scegli la ripresa"
              choices={OPENINGS_RESUME_CHOICES}
              error={errors.openings_resume}
              {...register('openings_resume')}
            />
            <ConsecutiveLossFields />
            <FormField
              id="flow-default-stop-loss"
              label="Stop loss predefinito (%)"
              error={errors.default_stop_loss_percent?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('default_stop_loss_percent')}
                  inputMode="decimal"
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <FormField
              id="flow-default-take-profit"
              label="Take profit predefinito (%)"
              error={errors.default_take_profit_percent?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('default_take_profit_percent')}
                  inputMode="decimal"
                  className={FORM_CONTROL}
                />
              )}
            </FormField>
            <TrailingStopFields />
            <FormField
              id="flow-minimum-confidence"
              label="Confidenza minima (0-100)"
              error={errors.minimum_confidence?.message}
            >
              {(control) => (
                <input
                  {...control}
                  {...register('minimum_confidence')}
                  inputMode="numeric"
                  className={FORM_CONTROL}
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
                className={FORM_CONTROL}
              />
            )}
          </FormField>
          <label className="flex items-center gap-2">
            <input type="checkbox" {...register('bring_to_minimum')} />
            Porta le aperture al minimo dell&apos;exchange
          </label>
          <button
            type="submit"
            disabled={isSubmitting || !tradable.isSuccess}
            className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
          >
            {submitLabel}
          </button>
        </form>
      </Card>
    </FormProvider>
  );
};
