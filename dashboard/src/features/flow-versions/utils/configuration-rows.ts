import type { Configuration } from '../api/get-flow-version';

export type ConfigurationRow = { readonly part: string; readonly value: string };

type Source = Configuration['sources'][number];

const NONE = 'nessuno';
const DEFAULT = 'predefinito';

const sortedEntries = (parameters: Record<string, string | number>): string[] =>
  Object.keys(parameters)
    .sort()
    .map((key) => `${key} ${parameters[key]}`);

const sourceText = (source: Source): string =>
  `${source.name} (peso ${source.weight}${sortedEntries(source.parameters)
    .map((entry) => `, ${entry}`)
    .join('')})`;

const percentText = (percent: string | null): string => (percent === null ? NONE : `${percent}%`);

// The labels of the API in its differences (R3.2.2).
const RESUME_LABELS: Readonly<Record<Configuration['openings_resume'], string>> = {
  manual: 'manuale',
  next_day: 'il giorno dopo',
};

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
  ];
};
