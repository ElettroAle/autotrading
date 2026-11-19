import type { TrialAdapter, TrialSource } from '../api/get-trial-sources';

import {
  adapterNamed,
  admittedRangeOf,
  defaultParametersOf,
  initialValuesOf,
  trialRequestOf,
  trialSchemaOf,
} from './trial-form';

const SERIES = {
  key: 'lunghezza_serie',
  label: 'lunghezza serie',
  default: 10,
  minimum: 1,
  maximum: 50,
};
const HYPERLIQUID: TrialAdapter = {
  name: 'Hyperliquid',
  description: 'mercato',
  parameters: [SERIES],
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

  it('asks no asset for a source of the whole market', () => {
    expect(
      trialRequestOf(SENTIMENT, { adapter: 'CoinMarketCap', asset: 'BTC', parameters: {} }).asset,
    ).toBeNull();
  });
});
