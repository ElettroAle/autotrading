import type { components } from '@/lib/api-schema';

import type { Configuration } from '../api/get-flow-version';

import { configurationRows } from './configuration-rows';

const CONFIGURATION: Configuration = {
  version: 2,
  assets: ['BTC', 'ETH'],
  cycle_minutes: 30,
  model: { name: 'openrouter/deepseek-chat', parameters: { temperature: '0.5', effort: 'alto' } },
  sources: [
    { name: 'notizie', weight: 7, parameters: { hours: 6 } },
    { name: 'indicatori', weight: 5, parameters: {} },
  ],
  instructions: 'prudente',
  risk_limits: {
    max_leverage: 5,
    max_margin_exposure_percent: '10',
    max_value_exposure_percent: null,
    max_total_margin_exposure_percent: '30',
    max_total_value_exposure_percent: null,
  },
  allocated_capital: '400',
  bring_to_minimum: true,
  system_prompt: '{instructions}\nRegole operative:\n- leva da 1 a {max_leverage}',
  system_prompt_is_default: false,
  max_consecutive_failures: 3,
};

// Every field of a configuration the API returns, with the names of the parts its differences give it; no part for the
// fields that are not compared. A new field of the API fails the types until it is placed here.
const PARTS_OF_FIELD = {
  version: [],
  assets: ['asset'],
  cycle_minutes: ['intervallo di ciclo'],
  model: ['modello', 'parametri del modello'],
  sources: ['fonti'],
  instructions: ['istruzioni'],
  risk_limits: [
    'leva massima',
    'esposizione massima del margine',
    'esposizione massima del valore',
    'esposizione complessiva massima del margine',
    'esposizione complessiva massima del valore',
  ],
  allocated_capital: ['capitale allocato'],
  bring_to_minimum: ['porta al minimo'],
  system_prompt: ['system prompt'],
  system_prompt_is_default: [],
  system_prompt_placeholders: [],
  max_consecutive_failures: ['cicli falliti consecutivi massimi'],
} as const satisfies Record<
  keyof components['schemas']['ConfigurationResponse'],
  readonly string[]
>;

describe('configurationRows', () => {
  it('names every part of the configuration as the API compares it, with its value as text', () => {
    expect(configurationRows(CONFIGURATION)).toEqual([
      { part: 'asset', value: 'BTC, ETH' },
      { part: 'intervallo di ciclo', value: '30 minuti' },
      { part: 'modello', value: 'openrouter/deepseek-chat' },
      { part: 'parametri del modello', value: 'effort alto, temperature 0.5' },
      { part: 'fonti', value: 'notizie (peso 7, hours 6); indicatori (peso 5)' },
      { part: 'istruzioni', value: 'prudente' },
      { part: 'leva massima', value: '5' },
      { part: 'esposizione massima del margine', value: '10%' },
      { part: 'esposizione massima del valore', value: 'nessuno' },
      { part: 'esposizione complessiva massima del margine', value: '30%' },
      { part: 'esposizione complessiva massima del valore', value: 'nessuno' },
      { part: 'capitale allocato', value: '400' },
      { part: 'porta al minimo', value: 'sì' },
      {
        part: 'system prompt',
        value: '{instructions}\nRegole operative:\n- leva da 1 a {max_leverage}',
      },
      { part: 'cicli falliti consecutivi massimi', value: '3' },
    ]);
  });

  it('has a row for every field of the configuration the API compares', () => {
    const parts = configurationRows(CONFIGURATION).map((row) => row.part);

    expect(parts).toEqual(Object.values(PARTS_OF_FIELD).flat());
  });

  it('says predefinito for the system prompt that follows the platform', () => {
    const rows = configurationRows({ ...CONFIGURATION, system_prompt_is_default: true });

    expect(rows.find((row) => row.part === 'system prompt')?.value).toBe('predefinito');
  });

  it('says nessuno for the parts left empty', () => {
    const rows = configurationRows({
      ...CONFIGURATION,
      model: { name: 'openai/gpt-4o', parameters: {} },
      sources: [],
      risk_limits: {
        max_leverage: null,
        max_margin_exposure_percent: null,
        max_value_exposure_percent: '12.5',
        max_total_margin_exposure_percent: null,
        max_total_value_exposure_percent: null,
      },
      bring_to_minimum: false,
      max_consecutive_failures: null,
    });

    expect(Object.fromEntries(rows.map((row) => [row.part, row.value]))).toMatchObject({
      'parametri del modello': 'nessuno',
      fonti: 'nessuno',
      'leva massima': 'nessuno',
      'esposizione massima del margine': 'nessuno',
      'esposizione massima del valore': '12.5%',
      'esposizione complessiva massima del margine': 'nessuno',
      'esposizione complessiva massima del valore': 'nessuno',
      'porta al minimo': 'no',
      'cicli falliti consecutivi massimi': 'nessuno',
    });
  });
});
