import type { Configuration } from '../api/get-flow-version';

export type ConfigurationRow = { readonly part: string; readonly value: string };

type Source = Configuration['sources'][number];

const NONE = 'nessuno';

const sortedEntries = (parameters: Record<string, string | number>): string[] =>
  Object.keys(parameters)
    .sort()
    .map((key) => `${key} ${parameters[key]}`);

const sourceText = (source: Source): string =>
  `${source.name} (peso ${source.weight}${sortedEntries(source.parameters)
    .map((entry) => `, ${entry}`)
    .join('')})`;

const percentText = (percent: string | null): string => (percent === null ? NONE : `${percent}%`);

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
    { part: 'capitale allocato', value: configuration.allocated_capital ?? NONE },
    { part: 'porta al minimo', value: configuration.bring_to_minimum ? 'sì' : 'no' },
  ];
};
