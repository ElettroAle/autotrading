import {
  defaultTextOf,
  isList,
  isListText,
  listOf,
  listRangeOf,
  listRefusalOf,
  listTextOf,
  parameterTextOf,
} from './parameter-lists';

const TREND_DAYS = {
  kind: 'list' as const,
  label: 'tendenza giorni',
  default: [7, 30],
  minimum: 1,
  maximum: 3650,
  maximum_values: 3,
};
const SERIES = {
  kind: 'number' as const,
  label: 'lunghezza serie',
  default: 10,
  minimum: 1,
  maximum: 50,
  maximum_values: null,
};

describe('the list parameters of the catalog (ADR parametri-delle-fonti-come-liste-libere)', () => {
  it('tells a list from a whole number by the kind the catalog declares', () => {
    expect([isList(TREND_DAYS), isList(SERIES)]).toEqual([true, false]);
  });

  it('accepts whole numbers separated by commas or spaces, and nothing at all', () => {
    expect(['7, 30, 90', '7 30', '', '  ', '7,'].map(isListText)).toEqual([
      true,
      true,
      true,
      true,
      true,
    ]);
    expect(['7; 30', '7.5', '-7', 'sette'].map(isListText)).toEqual([false, false, false, false]);
  });

  it('reads the numbers written in the order typed, nothing for a blank field', () => {
    expect(listOf(' 90, 7 30,')).toEqual([90, 7, 30]);
    expect(listOf('')).toEqual([]);
  });

  it('writes a list as the user types it and the default of either kind', () => {
    expect(listTextOf([7, 30, 90])).toEqual('7, 30, 90');
    expect([defaultTextOf(TREND_DAYS), defaultTextOf(SERIES)]).toEqual(['7, 30', '10']);
  });

  it('says the range of every value and how many values the list admits', () => {
    expect(listRangeOf(TREND_DAYS)).toEqual('ogni valore tra 1 e 3650, al massimo 3 valori');
  });

  it('refuses a value out of the range or too many values with the reasons of the API', () => {
    expect(listRefusalOf(TREND_DAYS, [7, 0])).toEqual('tendenza giorni: ogni valore tra 1 e 3650');
    expect(listRefusalOf(TREND_DAYS, [1, 2, 3, 4])).toEqual('tendenza giorni: al massimo 3 valori');
    expect(listRefusalOf(TREND_DAYS, [7, 7, 30, 90])).toBeUndefined();
    expect(listRefusalOf({ ...TREND_DAYS, maximum_values: null }, [1, 2, 3, 4])).toBeUndefined();
  });

  it('shows a saved list as the API writes it in the differences', () => {
    expect([parameterTextOf([7, 30]), parameterTextOf(10), parameterTextOf('0.5')]).toEqual([
      '[7, 30]',
      '10',
      '0.5',
    ]);
  });
});
