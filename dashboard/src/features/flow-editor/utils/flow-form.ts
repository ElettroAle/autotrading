import type { Path } from 'react-hook-form';
import { z } from 'zod';

import { isListText, LIST_SHAPE, listOf, listTextOf } from '@/lib/parameter-lists';

import { isDraft, type Flow } from '../api/get-flow';

// The form checks only the shape of what the user types; the rules and their reasons stay with the API (ADR 0130).
const NUMBER = /^\s*(\d+([.,]\d+)?)?\s*$/;
const numberText = z.string().regex(NUMBER, 'Inserisci un numero');
// A list parameter as typed: blank is the empty list, the value switched off (ADR parametri-delle-fonti-come-liste-libere).
const listText = z.string().refine(isListText, LIST_SHAPE);

// The same interval and reason as the API, so the refusal reads alike before and after sending (R3.2.2, ADR
// perdita-massima-nella-dashboard).
const MAX_LOSS_RANGE = 'la perdita massima va da 0,1 a 100';
const withinMaxLoss = (text: string): boolean => {
  if (text.trim() === '') {
    return true;
  }
  const percent = Number(text.trim().replace(',', '.'));
  return percent >= 0.1 && percent <= 100;
};
const maxLossText = numberText.refine(withinMaxLoss, MAX_LOSS_RANGE);

export const OPENINGS_RESUMES = ['manual', 'next_day'] as const;
export type OpeningsResume = (typeof OPENINGS_RESUMES)[number];

// An adapter never chosen has only its choice: weight and parameters show once it is chosen (R4.1.1); the list
// parameters stay apart from the whole numbers, so their kind travels with the form and never with their key.
const adapterValuesSchema = z.object({
  active: z.boolean(),
  weight: numberText.optional(),
  parameters: z.record(z.string(), numberText).optional(),
  lists: z.record(z.string(), listText).optional(),
});

// A source never activated has only its choice: its adapters show once it is active (R4.1.1).
const sourceValuesSchema = z.object({
  active: z.boolean(),
  adapters: z.record(z.string(), adapterValuesSchema).optional(),
});

// The name of an adapter may hold a dot ("alternative.me"), which the form reads as a step of the path of a field: the
// key of its values keeps it encoded.
const DOT = /\./g;
const ENCODED_DOT = '%2E';

/** The key of the values of an adapter in the form, its name with nothing the form reads as a path. */
export const adapterKeyOf = (name: string): string =>
  encodeURIComponent(name).replace(DOT, ENCODED_DOT);

const adapterNameOf = (key: string): string => decodeURIComponent(key);

// Decisions and days are disabled while the memory is off, and a disabled field gives no value (R5.3.4).
const memoryValuesSchema = z.object({
  active: z.boolean(),
  decisions: numberText.optional(),
  days: numberText.optional(),
});

export const flowFormSchema = z.object({
  name: z.string(),
  account_id: z.string(),
  assets: z.array(z.string()),
  cycle_minutes: numberText,
  model: z.string(),
  model_parameters: z.record(z.string(), z.string()),
  sources: z.record(z.string(), sourceValuesSchema),
  instructions: z.string(),
  max_leverage: numberText,
  max_margin_exposure_percent: numberText,
  max_value_exposure_percent: numberText,
  max_total_margin_exposure_percent: numberText,
  max_total_value_exposure_percent: numberText,
  default_stop_loss_percent: numberText,
  default_take_profit_percent: numberText,
  minimum_confidence: numberText,
  allocated_capital: numberText,
  bring_to_minimum: z.boolean(),
  // The text the user wrote, kept apart from whether the flow follows the default of the platform (R1.4.8).
  system_prompt: z.string(),
  system_prompt_default: z.boolean(),
  max_consecutive_failures: numberText,
  max_daily_loss_percent: maxLossText,
  max_drawdown_percent: maxLossText,
  openings_resume: z.enum(OPENINGS_RESUMES, 'Scegli la ripresa delle aperture'),
  memory: memoryValuesSchema,
});

export type FlowFormValues = z.infer<typeof flowFormSchema>;
export type SourceValues = z.infer<typeof sourceValuesSchema>;
export type AdapterValues = z.infer<typeof adapterValuesSchema>;
type MemoryValues = z.infer<typeof memoryValuesSchema>;

type AdapterRequest = {
  readonly name: string;
  readonly weight: number | null;
  readonly parameters: Record<string, number | number[]>;
};

type SourceRequest = {
  readonly name: string;
  readonly adapters: AdapterRequest[];
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
  // Null: no overall limit on the sum of the open positions (R3.2.1).
  max_total_margin_exposure_percent: string | null;
  max_total_value_exposure_percent: string | null;
  // Blank at creation takes the default stop loss of the platform; the take profit may stay absent (R3.1.2).
  default_stop_loss_percent: string | null;
  default_take_profit_percent: string | null;
  // Absent unless the user sets one: every opening goes on whatever the confidence of the agent (R3.1.4).
  minimum_confidence: number | null;
  bring_to_minimum: boolean;
  // Null follows the default of the platform (R1.4.8).
  system_prompt: string | null;
  // Null: no maximum, the flow keeps trying at every cycle (R3.2.4).
  max_consecutive_failures: number | null;
  // Null: no suspension of the openings for that loss (R3.2.2).
  max_daily_loss_percent: string | null;
  max_drawdown_percent: string | null;
  openings_resume: OpeningsResume;
  // Null decisions or days keep those in force, or the defaults of the platform at creation (R5.3.4).
  memory: { active: boolean; decisions: number | null; days: number | null };
};

export type CreationRequest = SettingsRequest & { name: string; allocated_capital?: string };

/** What the configuration of a flow saves besides its settings: its name, and the capital of a draft. */
type ModificationRequest = SettingsRequest & { name: string; allocated_capital: string };

/** What a modification sends: the changed settings, and the new capital of a flow out of draft when it changed. */
export type FlowChanges = { settings: Partial<ModificationRequest>; capital?: string };

export const emptyFormValues = (): FlowFormValues => ({
  name: '',
  account_id: '',
  assets: [],
  cycle_minutes: '',
  model: '',
  model_parameters: {},
  sources: {},
  instructions: '',
  max_leverage: '',
  max_margin_exposure_percent: '',
  max_value_exposure_percent: '',
  max_total_margin_exposure_percent: '',
  max_total_value_exposure_percent: '',
  default_stop_loss_percent: '',
  default_take_profit_percent: '',
  minimum_confidence: '',
  allocated_capital: '',
  bring_to_minimum: false,
  system_prompt: '',
  system_prompt_default: true,
  max_consecutive_failures: '',
  max_daily_loss_percent: '',
  max_drawdown_percent: '',
  openings_resume: 'manual',
  memory: { active: false, decisions: '', days: '' },
});

const decimalOf = (text: string): string => text.trim().replace(',', '.');

const isBlank = (text: string): boolean => text.trim() === '';

const decimalOrNull = (text: string): string | null => (isBlank(text) ? null : decimalOf(text));

const numberOrNull = (text: string): number | null =>
  isBlank(text) ? null : Number(decimalOf(text));

// A blank parameter takes the default the catalog declares.
const filledOf = (values: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => !isBlank(value))
      .map(([key, value]) => [key, decimalOf(value)]),
  );

const adaptersOf = (adapters: Record<string, AdapterValues>): AdapterRequest[] =>
  Object.entries(adapters)
    .filter(([, adapter]) => adapter.active)
    .map(([key, adapter]) => ({
      name: adapterNameOf(key),
      weight: numberOrNull(adapter.weight ?? ''),
      parameters: {
        ...Object.fromEntries(
          Object.entries(filledOf(adapter.parameters ?? {})).map(([parameter, value]) => [
            parameter,
            Number(value),
          ]),
        ),
        ...Object.fromEntries(
          Object.entries(adapter.lists ?? {}).map(([parameter, typed]) => [
            parameter,
            listOf(typed),
          ]),
        ),
      },
    }));

// An active source goes with the adapters chosen, none included: the API refuses it with the reason (R4.1.1).
const sourcesOf = (sources: Record<string, SourceValues>): SourceRequest[] =>
  Object.entries(sources)
    .filter(([, source]) => source.active)
    .map(([name, source]) => ({ name, adapters: adaptersOf(source.adapters ?? {}) }));

// Off, the memory sends no decisions nor days: the API keeps those in force, or its defaults at creation (R5.3.4).
const memoryOf = (memory: MemoryValues): SettingsRequest['memory'] =>
  memory.active
    ? {
        active: true,
        decisions: numberOrNull(memory.decisions ?? ''),
        days: numberOrNull(memory.days ?? ''),
      }
    : { active: false, decisions: null, days: null };

const settingsOf = (values: FlowFormValues): SettingsRequest => ({
  account_id: values.account_id,
  assets: values.assets,
  cycle_minutes: numberOrNull(values.cycle_minutes),
  model: values.model,
  model_parameters: filledOf(values.model_parameters),
  sources: sourcesOf(values.sources),
  instructions: values.instructions,
  max_leverage: numberOrNull(values.max_leverage),
  max_margin_exposure_percent: decimalOrNull(values.max_margin_exposure_percent),
  max_value_exposure_percent: decimalOrNull(values.max_value_exposure_percent),
  max_total_margin_exposure_percent: decimalOrNull(values.max_total_margin_exposure_percent),
  max_total_value_exposure_percent: decimalOrNull(values.max_total_value_exposure_percent),
  default_stop_loss_percent: decimalOrNull(values.default_stop_loss_percent),
  default_take_profit_percent: decimalOrNull(values.default_take_profit_percent),
  minimum_confidence: numberOrNull(values.minimum_confidence),
  bring_to_minimum: values.bring_to_minimum,
  system_prompt: values.system_prompt_default ? null : values.system_prompt,
  max_consecutive_failures: numberOrNull(values.max_consecutive_failures),
  max_daily_loss_percent: decimalOrNull(values.max_daily_loss_percent),
  max_drawdown_percent: decimalOrNull(values.max_drawdown_percent),
  openings_resume: values.openings_resume,
  memory: memoryOf(values.memory),
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

/** The saved parameters of an adapter as the form holds them: the whole numbers, and the lists apart. */
const valuesOfParameters = (
  parameters: Record<string, number | number[]>,
): Pick<AdapterValues, 'parameters' | 'lists'> => {
  const entries = Object.entries(parameters);
  return {
    parameters: Object.fromEntries(
      entries.flatMap(([key, value]) => (typeof value === 'number' ? [[key, String(value)]] : [])),
    ),
    lists: Object.fromEntries(
      entries.flatMap(([key, value]) =>
        typeof value === 'number' ? [] : [[key, listTextOf(value)]],
      ),
    ),
  };
};

/** The form filled with the configuration version in force of the flow. */
export const formValuesOf = (flow: Flow): FlowFormValues => ({
  name: flow.name,
  // A draft has neither account nor capital yet (ADR 0124).
  account_id: flow.account_id ?? '',
  assets: [...flow.assets],
  cycle_minutes: String(flow.cycle_minutes),
  model: flow.model.name,
  model_parameters: { ...flow.model.parameters },
  sources: Object.fromEntries(
    flow.sources.map((source) => [
      source.name,
      {
        active: true,
        adapters: Object.fromEntries(
          source.adapters.map((adapter) => [
            adapterKeyOf(adapter.name),
            {
              active: true,
              weight: String(adapter.weight),
              ...valuesOfParameters(adapter.parameters),
            },
          ]),
        ),
      },
    ]),
  ),
  instructions: flow.instructions,
  max_leverage: textOf(flow.risk_limits.max_leverage),
  max_margin_exposure_percent: textOf(flow.risk_limits.max_margin_exposure_percent),
  max_value_exposure_percent: textOf(flow.risk_limits.max_value_exposure_percent),
  max_total_margin_exposure_percent: textOf(flow.risk_limits.max_total_margin_exposure_percent),
  max_total_value_exposure_percent: textOf(flow.risk_limits.max_total_value_exposure_percent),
  default_stop_loss_percent: flow.default_stop_loss_percent,
  default_take_profit_percent: textOf(flow.default_take_profit_percent),
  minimum_confidence: textOf(flow.minimum_confidence),
  allocated_capital: flow.allocated_capital ?? '',
  bring_to_minimum: flow.bring_to_minimum,
  system_prompt: flow.system_prompt_is_default ? '' : flow.system_prompt,
  system_prompt_default: flow.system_prompt_is_default,
  max_consecutive_failures: textOf(flow.max_consecutive_failures),
  max_daily_loss_percent: textOf(flow.max_daily_loss_percent),
  max_drawdown_percent: textOf(flow.max_drawdown_percent),
  openings_resume: flow.openings_resume,
  memory: {
    active: flow.memory.active,
    decisions: String(flow.memory.decisions),
    days: String(flow.memory.days),
  },
});

const sameValue = (one: unknown, other: unknown): boolean =>
  JSON.stringify(one) === JSON.stringify(other);

const MODEL: keyof SettingsRequest = 'model';
const MODEL_PARAMETERS: keyof SettingsRequest = 'model_parameters';
// Their null is a value: back to the default of the platform (R1.4.8), an exposure limit removed (R1.1.3, R3.2.1),
// the maximum of consecutive failed cycles removed (R3.2.4), a maximum loss removed (R3.2.2), the default take profit
// removed (R3.1.2), the minimum confidence removed (R3.1.4).
const NULL_IS_A_VALUE = new Set<keyof SettingsRequest>([
  'system_prompt',
  'max_margin_exposure_percent',
  'max_value_exposure_percent',
  'max_total_margin_exposure_percent',
  'max_total_value_exposure_percent',
  'max_consecutive_failures',
  'max_daily_loss_percent',
  'max_drawdown_percent',
  'default_take_profit_percent',
  'minimum_confidence',
]);

/** The new name, when the user changed it (ADR nome-del-flusso-modificabile). */
const nameChangeOf = (flow: Flow, values: FlowFormValues): Partial<ModificationRequest> => {
  const name = values.name.trim();
  return name === flow.name ? {} : { name };
};

/**
 * Only the settings the user changed (R1.1.3): a part left out keeps the value in force, so an emptied one is not
 * sent, unless its null says something; a new model goes with its parameters, as they belong to it. The capital of a
 * draft goes with them; that of any other flow stays apart, with its own command (R1.1.7, ADR
 * assegnazione-della-bozza-nel-form-di-configurazione).
 */
export const changesOf = (flow: Flow, values: FlowFormValues): FlowChanges => {
  const before = settingsOf(formValuesOf(flow));
  const after = settingsOf(values);
  const changed = (Object.keys(after) as (keyof SettingsRequest)[]).filter(
    (key) =>
      (after[key] !== null || NULL_IS_A_VALUE.has(key)) && !sameValue(before[key], after[key]),
  );
  const keys = changed.includes(MODEL) ? [...new Set([...changed, MODEL_PARAMETERS])] : changed;
  const settings = {
    ...nameChangeOf(flow, values),
    ...Object.fromEntries(keys.map((key) => [key, after[key]])),
  };
  const capital = decimalOf(values.allocated_capital);
  if (capital === decimalOf(flow.allocated_capital ?? '')) {
    return { settings };
  }
  return isDraft(flow)
    ? { settings: { ...settings, allocated_capital: capital } }
    : { settings, capital };
};

const MEMORY_FIELDS: readonly Path<FlowFormValues>[] = ['memory.decisions', 'memory.days'];
const FORM_FIELDS = new Set<string>([...Object.keys(flowFormSchema.shape), ...MEMORY_FIELDS]);

/** The field of the form a setting named by the API is typed in, when the form has it. */
export const formFieldOf = (setting: string): Path<FlowFormValues> | undefined =>
  FORM_FIELDS.has(setting) ? (setting as Path<FlowFormValues>) : undefined;
