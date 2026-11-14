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
  },
  allocated_capital: '400',
  bring_to_minimum: true,
};

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
      { part: 'capitale allocato', value: '400' },
      { part: 'porta al minimo', value: 'sì' },
    ]);
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
      },
      bring_to_minimum: false,
    });

    expect(Object.fromEntries(rows.map((row) => [row.part, row.value]))).toMatchObject({
      'parametri del modello': 'nessuno',
      fonti: 'nessuno',
      'leva massima': 'nessuno',
      'esposizione massima del margine': 'nessuno',
      'esposizione massima del valore': '12.5%',
      'porta al minimo': 'no',
    });
  });
});
