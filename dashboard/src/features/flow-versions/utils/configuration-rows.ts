import { parameterTextOf } from '@/lib/parameter-lists';

import type { Configuration } from '../api/get-flow-version';

export type ConfigurationRow = { readonly part: string; readonly value: string };

type Source = Configuration['sources'][number];

const NONE = 'nessuno';
const NO_MINIMUM_CONFIDENCE = 'nessuna';
const DEFAULT = 'predefinito';

// A list parameter reads as the API writes it in the differences (ADR parametri-delle-fonti-come-liste-libere).
const sortedEntries = (parameters: Record<string, string | number | readonly number[]>): string[] =>
  Object.entries(parameters)
    .sort(([one], [other]) => (one < other ? -1 : 1))
    .map(([key, value]) => `${key} ${parameterTextOf(value)}`);

// Every adapter of a source with its weight and parameters, «fonte · adapter», as the API names it (R4.1.1).
const sourceText = (source: Source): string =>
  source.adapters
    .map(
      (adapter) =>
        `${source.name} · ${adapter.name} (peso ${adapter.weight}${sortedEntries(adapter.parameters)
          .map((entry) => `, ${entry}`)
          .join('')})`,
    )
    .join('; ');

const percentText = (percent: string | null): string => (percent === null ? NONE : `${percent}%`);

// The labels of the API in its differences (R3.2.2).
const RESUME_LABELS: Readonly<Record<Configuration['openings_resume'], string>> = {
  manual: 'manuale',
  next_day: 'il giorno dopo',
};

// The memory as the API writes it in its differences (R5.3.4, R5.3.5, R5.3.7).
const memoryText = (memory: Configuration['memory']): string => {
  if (!memory.active) {
    return 'non attiva';
  }
  const motive =
    memory.text_length === null ? 'motivo intero' : `motivo fino a ${memory.text_length} caratteri`;
  const which = memory.all_decisions
    ? 'tutte le decisioni'
    : 'solo aperture, chiusure e inversioni';
  const options = [
    memory.summary ? ['riepilogo'] : [],
    memory.other_assets ? ['altri asset'] : [],
  ].flat();
  return [
    `attiva, ${memory.decisions} decisioni, ${memory.days} giorni`,
    motive,
    which,
    ...options,
  ].join(', ');
};

// The block of the reopenings as the API writes it in its differences (R5.5.2).
const consecutiveLossLimitText = (limit: Configuration['consecutive_loss_limit']): string =>
  limit === null
    ? NONE
    : `${limit.max_consecutive_losses} perdite consecutive in ${limit.loss_window_hours} ore, blocco di ${limit.block_minutes} minuti, ambito ${limit.count_scope}`;

/**
 * The parts of a configuration with the names the API gives them in its differences (R1.1.3), so the comparison
 * highlights a row by the name of the part the API reports as changed.
 */
export const configurationRows = (configuration: Configuration): ConfigurationRow[] => {
  const limits = configuration.risk_limits;
  return [
    { part: 'asset', value: configuration.assets.join(', ') },
    { part: 'intervallo di ciclo', value: `${configuration.cycle_minutes} minuti` },
    { part: 'modello', value: configuration.model.name },
    {
      part: 'parametri del modello',
      value: sortedEntries(configuration.model.parameters).join(', ') || NONE,
    },
    { part: 'fonti', value: configuration.sources.map(sourceText).join('; ') || NONE },
    { part: 'istruzioni', value: configuration.instructions },
    { part: 'leva massima', value: String(limits.max_leverage ?? NONE) },
    {
      part: 'esposizione massima del margine',
      value: percentText(limits.max_margin_exposure_percent),
    },
    {
      part: 'esposizione massima del valore',
      value: percentText(limits.max_value_exposure_percent),
    },
    {
      part: 'esposizione complessiva massima del margine',
      value: percentText(limits.max_total_margin_exposure_percent),
    },
    {
      part: 'esposizione complessiva massima del valore',
      value: percentText(limits.max_total_value_exposure_percent),
    },
    { part: 'stop loss predefinito', value: percentText(configuration.default_stop_loss_percent) },
    {
      part: 'take profit predefinito',
      value: percentText(configuration.default_take_profit_percent),
    },
    // The stop that follows the price beside the other protections, as the API names its parts (R5.5.1).
    {
      part: 'distanza dello stop che segue',
      value: percentText(configuration.trailing_stop.distance_percent),
    },
    {
      part: 'attivazione dello stop che segue',
      value: percentText(configuration.trailing_stop.activation_percent),
    },
    { part: 'pareggio', value: percentText(configuration.trailing_stop.breakeven_percent) },
    {
      part: "massimo profitto raggiunto nel contesto dell'agente",
      value: configuration.trailing_stop.max_profit_in_context ? 'sì' : 'no',
    },
    {
      part: 'confidenza minima',
      value: String(configuration.minimum_confidence ?? NO_MINIMUM_CONFIDENCE),
    },
    { part: 'capitale allocato', value: configuration.allocated_capital ?? NONE },
    { part: 'porta al minimo', value: configuration.bring_to_minimum ? 'sì' : 'no' },
    {
      part: 'system prompt',
      value: configuration.system_prompt_is_default ? DEFAULT : configuration.system_prompt,
    },
    {
      part: 'cicli falliti consecutivi massimi',
      value: String(configuration.max_consecutive_failures ?? NONE),
    },
    {
      part: 'perdita giornaliera massima',
      value: percentText(configuration.max_daily_loss_percent),
    },
    { part: 'perdita massima dal picco', value: percentText(configuration.max_drawdown_percent) },
    { part: 'ripresa delle aperture', value: RESUME_LABELS[configuration.openings_resume] },
    {
      part: 'blocco delle riaperture dopo perdite consecutive',
      value: consecutiveLossLimitText(configuration.consecutive_loss_limit),
    },
    { part: 'memoria', value: memoryText(configuration.memory) },
    {
      part: "esposizione del conto nel contesto dell'agente",
      value: configuration.account_exposure_for_agent ? 'sì' : 'no',
    },
    {
      part: "commissioni nel contesto dell'agente",
      value: configuration.fees_for_agent ? 'sì' : 'no',
    },
  ];
};
