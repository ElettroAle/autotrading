import type { TrialAdapter, TrialParameter, TrialSource } from '../api/get-trial-sources';

import {
  adapterNamed,
  admittedRangeOf,
  defaultParametersOf,
  initialValuesOf,
  trialRequestOf,
  trialSchemaOf,
} from './trial-form';

const SERIES: TrialParameter = {
  key: 'lunghezza_serie',
  label: 'lunghezza serie',
  kind: 'number',
  default: 10,
  minimum: 1,
  maximum: 50,
  choices: [],
  maximum_values: null,
};
const HORIZON: TrialParameter = {
  key: 'orizzonte',
  label: 'orizzonte',
  kind: 'number',
  default: 0,
  minimum: 0,
  maximum: 10080,
  choices: [
    { value: 0, label: 'nessuno' },
    { value: 1440, label: '1 giorno' },
  ],
  maximum_values: null,
};
const TREND_DAYS: TrialParameter = {
  key: 'tendenza_giorni',
  label: 'tendenza giorni',
  kind: 'list',
  default: [7, 30],
  minimum: 1,
  maximum: 3650,
  choices: [],
  maximum_values: 3,
};
const HYPERLIQUID: TrialAdapter = {
  name: 'Hyperliquid',
  description: 'mercato',
  parameters: [SERIES],
};
const WITH_LIST: TrialSource = {
  name: 'indicatori',
  description: 'indicatori tecnici',
  per_asset: true,
  adapters: [{ ...HYPERLIQUID, parameters: [SERIES, TREND_DAYS] }],
};
const INDICATORS: TrialSource = {
  name: 'indicatori',
  description: 'indicatori tecnici',
  per_asset: true,
  adapters: [HYPERLIQUID],
};
const SENTIMENT: TrialSource = {
  name: 'sentiment',
  description: 'fear and greed',
  per_asset: false,
  adapters: [
    { name: 'alternative.me', description: 'gratuito', parameters: [] },
    { name: 'CoinMarketCap', description: 'a pagamento', parameters: [] },
  ],
};

const reasonsOf = (source: TrialSource, values: unknown): string[] => {
  const result = trialSchemaOf(source, adapterNamed(source, 'Hyperliquid')).safeParse(values);
  return result.success ? [] : result.error.issues.map((issue) => issue.message);
};

describe('the form of a trial (ADR pagina-fonti-con-la-prova)', () => {
  it('says the values a parameter admits', () => {
    expect(admittedRangeOf(SERIES)).toBe('ammesso da 1 a 50');
  });

  it('says the choices a parameter with choices admits', () => {
    expect(admittedRangeOf(HORIZON)).toBe('ammessi nessuno, 1 giorno');
  });

  it.each([
    ['1440', []],
    ['60', ['ammessi nessuno, 1 giorno']],
    ['', ['ammessi nessuno, 1 giorno']],
  ])('checks %j against the choices of the parameter', (typed, reasons) => {
    const prophet: TrialAdapter = {
      name: 'Prophet',
      description: 'previsioni',
      parameters: [HORIZON],
    };
    const forecast: TrialSource = { ...INDICATORS, name: 'forecast', adapters: [prophet] };
    const result = trialSchemaOf(forecast, prophet).safeParse({
      adapter: 'Prophet',
      asset: 'BTC',
      parameters: { orizzonte: typed },
    });

    expect(result.success ? [] : result.error.issues.map((issue) => issue.message)).toEqual(
      reasons,
    );
  });

  it('starts from the only adapter of the source at the defaults of the catalog', () => {
    expect(initialValuesOf(INDICATORS)).toEqual({
      adapter: 'Hyperliquid',
      asset: '',
      parameters: { lunghezza_serie: '10' },
    });
  });

  it('leaves the adapter to choose when the source has more than one', () => {
    expect(initialValuesOf(SENTIMENT)).toEqual({ adapter: '', asset: '', parameters: {} });
  });

  it('gives no parameters without an adapter', () => {
    expect(defaultParametersOf(undefined)).toEqual({});
  });

  it('accepts a whole value within the limits', () => {
    expect(
      reasonsOf(INDICATORS, {
        adapter: 'Hyperliquid',
        asset: 'BTC',
        parameters: { lunghezza_serie: '50' },
      }),
    ).toEqual([]);
  });

  it.each(['51', '0', '2.5', '', 'dieci'])('refuses %j with the admitted range', (typed) => {
    expect(
      reasonsOf(INDICATORS, {
        adapter: 'Hyperliquid',
        asset: 'BTC',
        parameters: { lunghezza_serie: typed },
      }),
    ).toEqual(['ammesso da 1 a 50']);
  });

  it('asks the asset of a source per asset', () => {
    expect(
      reasonsOf(INDICATORS, {
        adapter: 'Hyperliquid',
        asset: ' ',
        parameters: { lunghezza_serie: '10' },
      }),
    ).toEqual(["scegli l'asset"]);
  });

  it('asks no asset of a source of the whole market, but the adapter', () => {
    expect(reasonsOf(SENTIMENT, { adapter: '', asset: '', parameters: {} })).toEqual([
      "scegli l'adapter",
    ]);
  });

  it('asks the asset and the parameters as whole numbers for a source per asset', () => {
    expect(
      trialRequestOf(INDICATORS, {
        adapter: 'Hyperliquid',
        asset: ' BTC ',
        parameters: { lunghezza_serie: ' 12 ' },
      }),
    ).toEqual({
      source: 'indicatori',
      adapter: 'Hyperliquid',
      asset: 'BTC',
      parameters: { lunghezza_serie: 12 },
    });
  });

  // ADR parametri-delle-fonti-come-liste-libere: a list starts at its default and follows the common rules.
  it('starts a list parameter at its default list, as the user types it', () => {
    expect(initialValuesOf(WITH_LIST).parameters).toEqual({
      lunghezza_serie: '10',
      tendenza_giorni: '7, 30',
    });
  });

  it.each([
    ['7, 30, 90', []],
    ['', []],
    ['7; 30', ['Inserisci numeri interi separati da virgole']],
    ['7, 0', ['tendenza giorni: ogni valore tra 1 e 3650']],
    ['1 2 3 4', ['tendenza giorni: al massimo 3 valori']],
  ])('checks the list %j with the common rules', (typed, reasons) => {
    expect(
      reasonsOf(WITH_LIST, {
        adapter: 'Hyperliquid',
        asset: 'BTC',
        parameters: { lunghezza_serie: '10', tendenza_giorni: typed },
      }),
    ).toEqual(reasons);
  });

  it('asks a list parameter as the list of numbers typed', () => {
    expect(
      trialRequestOf(WITH_LIST, {
        adapter: 'Hyperliquid',
        asset: 'BTC',
        parameters: { lunghezza_serie: '10', tendenza_giorni: '90, 7' },
      }).parameters,
    ).toEqual({ lunghezza_serie: 10, tendenza_giorni: [90, 7] });
  });

  it('asks no asset for a source of the whole market', () => {
    expect(
      trialRequestOf(SENTIMENT, { adapter: 'CoinMarketCap', asset: 'BTC', parameters: {} }).asset,
    ).toBeNull();
  });
});
