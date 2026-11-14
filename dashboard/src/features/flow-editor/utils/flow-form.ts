import { z } from 'zod';

import type { Flow } from '../api/get-flow';

// The form checks only the shape of what the user types; the rules and their reasons stay with the API (ADR 0130).
const NUMBER = /^\s*(\d+([.,]\d+)?)?\s*$/;
const numberText = z.string().regex(NUMBER, 'Inserisci un numero');

// A source never activated has only its choice: weight and parameters show once it is active.
const sourceValuesSchema = z.object({
  active: z.boolean(),
  weight: numberText.optional(),
  parameters: z.record(z.string(), numberText).optional(),
});

export const flowFormSchema = z.object({
  name: z.string(),
  account_id: z.string(),
  assets: z.string(),
  cycle_minutes: numberText,
  model: z.string(),
  model_parameters: z.record(z.string(), z.string()),
  sources: z.record(z.string(), sourceValuesSchema),
  instructions: z.string(),
  max_leverage: numberText,
  max_margin_exposure_percent: numberText,
  max_value_exposure_percent: numberText,
  allocated_capital: numberText,
  bring_to_minimum: z.boolean(),
});

export type FlowFormValues = z.infer<typeof flowFormSchema>;
export type SourceValues = z.infer<typeof sourceValuesSchema>;

type SourceRequest = {
  readonly name: string;
  readonly weight: number | null;
  readonly parameters: Record<string, number>;
};

/** The settings a version of the configuration has, as the API takes them. */
type SettingsRequest = {
  account_id: string;
  assets: string[];
  cycle_minutes: number | null;
  model: string;
  model_parameters: Record<string, string>;
  sources: SourceRequest[];
  instructions: string;
  max_leverage: number | null;
  max_margin_exposure_percent: string | null;
  max_value_exposure_percent: string | null;
  bring_to_minimum: boolean;
};

export type CreationRequest = SettingsRequest & { name: string; allocated_capital?: string };

/** What a modification sends: the changed settings, and the new capital when it changed. */
export type FlowChanges = { settings: Partial<SettingsRequest>; capital?: string };

export const emptyFormValues = (): FlowFormValues => ({
  name: '',
  account_id: '',
  assets: '',
  cycle_minutes: '',
  model: '',
  model_parameters: {},
  sources: {},
  instructions: '',
  max_leverage: '',
  max_margin_exposure_percent: '',
  max_value_exposure_percent: '',
  allocated_capital: '',
  bring_to_minimum: false,
});

const decimalOf = (text: string): string => text.trim().replace(',', '.');

const isBlank = (text: string): boolean => text.trim() === '';

const decimalOrNull = (text: string): string | null => (isBlank(text) ? null : decimalOf(text));

const numberOrNull = (text: string): number | null =>
  isBlank(text) ? null : Number(decimalOf(text));

const assetsOf = (text: string): string[] =>
  text
    .split(',')
    .map((asset) => asset.trim())
    .filter((asset) => asset !== '');

// A blank parameter takes the default the catalog declares.
const filledOf = (values: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => !isBlank(value))
      .map(([key, value]) => [key, decimalOf(value)]),
  );

const sourcesOf = (sources: Record<string, SourceValues>): SourceRequest[] =>
  Object.entries(sources)
    .filter(([, source]) => source.active)
    .map(([name, source]) => ({
      name,
      weight: numberOrNull(source.weight ?? ''),
      parameters: Object.fromEntries(
        Object.entries(filledOf(source.parameters ?? {})).map(([key, value]) => [
          key,
          Number(value),
        ]),
      ),
    }));

const settingsOf = (values: FlowFormValues): SettingsRequest => ({
  account_id: values.account_id,
  assets: assetsOf(values.assets),
  cycle_minutes: numberOrNull(values.cycle_minutes),
  model: values.model,
  model_parameters: filledOf(values.model_parameters),
  sources: sourcesOf(values.sources),
  instructions: values.instructions,
  max_leverage: numberOrNull(values.max_leverage),
  max_margin_exposure_percent: decimalOrNull(values.max_margin_exposure_percent),
  max_value_exposure_percent: decimalOrNull(values.max_value_exposure_percent),
  bring_to_minimum: values.bring_to_minimum,
});

/** The whole configuration of a new flow (R1.1.1); a blank capital is left out, so the API names it as missing. */
export const creationRequestOf = (values: FlowFormValues): CreationRequest => ({
  name: values.name.trim(),
  ...settingsOf(values),
  ...(isBlank(values.allocated_capital)
    ? {}
    : { allocated_capital: decimalOf(values.allocated_capital) }),
});

const textOf = (value: number | string | null): string => (value === null ? '' : String(value));

/** The form filled with the configuration version in force of the flow. */
export const formValuesOf = (flow: Flow): FlowFormValues => ({
  name: flow.name,
  // A draft has neither account nor capital yet (ADR 0124).
  account_id: flow.account_id ?? '',
  assets: flow.assets.join(', '),
  cycle_minutes: String(flow.cycle_minutes),
  model: flow.model.name,
  model_parameters: { ...flow.model.parameters },
  sources: Object.fromEntries(
    flow.sources.map((source) => [
      source.name,
      {
        active: true,
        weight: String(source.weight),
        parameters: Object.fromEntries(
          Object.entries(source.parameters).map(([key, value]) => [key, String(value)]),
        ),
      },
    ]),
  ),
  instructions: flow.instructions,
  max_leverage: textOf(flow.risk_limits.max_leverage),
  max_margin_exposure_percent: textOf(flow.risk_limits.max_margin_exposure_percent),
  max_value_exposure_percent: textOf(flow.risk_limits.max_value_exposure_percent),
  allocated_capital: flow.allocated_capital ?? '',
  bring_to_minimum: flow.bring_to_minimum,
});

const sameValue = (one: unknown, other: unknown): boolean =>
  JSON.stringify(one) === JSON.stringify(other);

const MODEL: keyof SettingsRequest = 'model';
const MODEL_PARAMETERS: keyof SettingsRequest = 'model_parameters';

/**
 * Only the settings the user changed (R1.1.3): a part left out keeps the value in force, so an emptied one is not
 * sent; a new model goes with its parameters, as they belong to it. The capital stays apart (R1.1.7).
 */
export const changesOf = (flow: Flow, values: FlowFormValues): FlowChanges => {
  const before = settingsOf(formValuesOf(flow));
  const after = settingsOf(values);
  const changed = (Object.keys(after) as (keyof SettingsRequest)[]).filter(
    (key) => after[key] !== null && !sameValue(before[key], after[key]),
  );
  const keys = changed.includes(MODEL) ? [...new Set([...changed, MODEL_PARAMETERS])] : changed;
  const settings = Object.fromEntries(keys.map((key) => [key, after[key]]));
  const capital = decimalOf(values.allocated_capital);
  return capital === decimalOf(flow.allocated_capital ?? '') ? { settings } : { settings, capital };
};

const FORM_FIELDS = new Set<string>(Object.keys(flowFormSchema.shape));

/** The field of the form a setting named by the API is typed in, when the form has it. */
export const formFieldOf = (setting: string): keyof FlowFormValues | undefined =>
  FORM_FIELDS.has(setting) ? (setting as keyof FlowFormValues) : undefined;
