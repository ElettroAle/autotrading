import { formatAmount, formatPercent, formatResult, formatUsd } from './format-number';

describe('formatAmount', () => {
  it('writes an amount of the API in Italian, without useless decimals', () => {
    expect(formatAmount('3')).toBe('3');
    expect(formatAmount('1234.5')).toBe('1234,5');
  });

  it('keeps at most two decimals', () => {
    expect(formatAmount('0.125')).toBe('0,13');
  });
});

describe('formatResult', () => {
  it('signs a gain and a loss', () => {
    expect(formatResult('15')).toBe('+15');
    expect(formatResult('-5')).toBe('-5');
  });

  it('leaves an even result without sign', () => {
    expect(formatResult('0')).toBe('0');
  });
});

describe('formatPercent', () => {
  it('writes a percentage with two decimals', () => {
    expect(formatPercent('50.00')).toBe('50,00%');
    expect(formatPercent('66.67')).toBe('66,67%');
  });
});

describe('formatUsd', () => {
  it('writes a cost with at least two decimals', () => {
    expect(formatUsd('1.2')).toBe('1,20');
    expect(formatUsd('0')).toBe('0,00');
  });

  it('keeps the decimals of a cost below the cent', () => {
    expect(formatUsd('0.0031')).toBe('0,0031');
  });
});
