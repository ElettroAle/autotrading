import type { components } from '@/lib/api-schema';

import type { Configuration } from '../api/get-flow-version';

import { configurationRows } from './configuration-rows';

const CONFIGURATION: Configuration = {
  version: 2,
  assets: ['BTC', 'ETH'],
  cycle_minutes: 30,
  model: { name: 'openrouter/deepseek-chat', parameters: { temperature: '0.5', effort: 'alto' } },
  sources: [
    {
      name: 'notizie',
      adapters: [{ name: 'RSS', weight: 7, parameters: { hours: 6, giorni: [7, 30] } }],
    },
    {
      name: 'sentiment',
      adapters: [
        { name: 'alternative.me', weight: 5, parameters: {} },
        { name: 'CoinMarketCap', weight: 3, parameters: {} },
      ],
    },
  ],
  instructions: 'prudente',
  risk_limits: {
    max_leverage: 5,
    max_margin_exposure_percent: '10',
    max_value_exposure_percent: null,
    max_total_margin_exposure_percent: '30',
    max_total_value_exposure_percent: null,
  },
  default_stop_loss_percent: '5',
  default_take_profit_percent: '10',
  minimum_confidence: 60,
  allocated_capital: '400',
  bring_to_minimum: true,
  system_prompt: '{instructions}\nRegole operative:\n- leva da 1 a {max_leverage}',
  system_prompt_is_default: false,
  max_consecutive_failures: 3,
  max_daily_loss_percent: '5',
  max_drawdown_percent: '12.5',
  openings_resume: 'next_day',
  memory: { active: true, decisions: 5, days: 14, text_length: null, all_decisions: true },
  trailing_stop: {
    distance_percent: '2',
    activation_percent: null,
    breakeven_percent: '1.5',
    max_profit_in_context: true,
  },
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
  default_stop_loss_percent: ['stop loss predefinito'],
  default_take_profit_percent: ['take profit predefinito'],
  trailing_stop: [
    'distanza dello stop che segue',
    'attivazione dello stop che segue',
    'pareggio',
    "massimo profitto raggiunto nel contesto dell'agente",
  ],
  minimum_confidence: ['confidenza minima'],
  allocated_capital: ['capitale allocato'],
  bring_to_minimum: ['porta al minimo'],
  system_prompt: ['system prompt'],
  system_prompt_is_default: [],
  system_prompt_placeholders: [],
  max_consecutive_failures: ['cicli falliti consecutivi massimi'],
  max_daily_loss_percent: ['perdita giornaliera massima'],
  max_drawdown_percent: ['perdita massima dal picco'],
  openings_resume: ['ripresa delle aperture'],
  memory: ['memoria'],
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
      {
        part: 'fonti',
        value:
          'notizie · RSS (peso 7, giorni [7, 30], hours 6); sentiment · alternative.me (peso 5); sentiment · CoinMarketCap (peso 3)',
      },
      { part: 'istruzioni', value: 'prudente' },
      { part: 'leva massima', value: '5' },
      { part: 'esposizione massima del margine', value: '10%' },
      { part: 'esposizione massima del valore', value: 'nessuno' },
      { part: 'esposizione complessiva massima del margine', value: '30%' },
      { part: 'esposizione complessiva massima del valore', value: 'nessuno' },
      { part: 'stop loss predefinito', value: '5%' },
      { part: 'take profit predefinito', value: '10%' },
      { part: 'distanza dello stop che segue', value: '2%' },
      { part: 'attivazione dello stop che segue', value: 'nessuno' },
      { part: 'pareggio', value: '1.5%' },
      { part: "massimo profitto raggiunto nel contesto dell'agente", value: 'sì' },
      { part: 'confidenza minima', value: '60' },
      { part: 'capitale allocato', value: '400' },
      { part: 'porta al minimo', value: 'sì' },
      {
        part: 'system prompt',
        value: '{instructions}\nRegole operative:\n- leva da 1 a {max_leverage}',
      },
      { part: 'cicli falliti consecutivi massimi', value: '3' },
      { part: 'perdita giornaliera massima', value: '5%' },
      { part: 'perdita massima dal picco', value: '12.5%' },
      { part: 'ripresa delle aperture', value: 'il giorno dopo' },
      {
        part: 'memoria',
        value: 'attiva, 5 decisioni, 14 giorni, motivo intero, tutte le decisioni',
      },
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
      default_take_profit_percent: null,
      minimum_confidence: null,
      bring_to_minimum: false,
      max_consecutive_failures: null,
      max_daily_loss_percent: null,
      max_drawdown_percent: null,
      openings_resume: 'manual',
      memory: { active: false, decisions: 10, days: 30, text_length: 160, all_decisions: false },
    });

    expect(Object.fromEntries(rows.map((row) => [row.part, row.value]))).toMatchObject({
      'parametri del modello': 'nessuno',
      fonti: 'nessuno',
      'leva massima': 'nessuno',
      'esposizione massima del margine': 'nessuno',
      'esposizione massima del valore': '12.5%',
      'esposizione complessiva massima del margine': 'nessuno',
      'esposizione complessiva massima del valore': 'nessuno',
      'take profit predefinito': 'nessuno',
      'confidenza minima': 'nessuna',
      'porta al minimo': 'no',
      'cicli falliti consecutivi massimi': 'nessuno',
      'perdita giornaliera massima': 'nessuno',
      'perdita massima dal picco': 'nessuno',
      'ripresa delle aperture': 'manuale',
      memoria: 'non attiva',
    });
  });
});
