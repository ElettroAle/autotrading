import {
  formatAmount,
  formatGain,
  formatPercent,
  formatPrice,
  formatRate,
  formatRoundedAmount,
  formatRoundedResult,
  formatSignedAmount,
  formatUsd,
} from './format-amount';

describe('formatAmount', () => {
  it.each([
    ['60000', '60.000'],
    ['0.01', '0,01'],
    ['1234567.125', '1.234.567,125'],
    ['999', '999'],
    ['-3150.5', '-3150,5'],
    ['12345', '12.345'],
    ['0', '0'],
  ])('writes the amount %s of the API in Italian, digit for digit, as %s', (amount, written) => {
    expect(formatAmount(amount)).toBe(written);
  });
});

describe('formatSignedAmount', () => {
  it.each([
    ['12', '+12'],
    ['-0.5', '-0,5'],
    ['0', '0'],
  ])('writes the amount %s with its sign as %s', (amount, written) => {
    expect(formatSignedAmount(amount)).toBe(written);
  });
});

describe('formatPercent', () => {
  it.each([
    ['5', '+5,00%'],
    ['-6.666666666666666666666666667', '-6,67%'],
    ['0', '0,00%'],
    ['1234.5', '+1234,50%'],
    ['12345.5', '+12.345,50%'],
  ])('writes the percent %s with its sign and two decimals as %s', (percent, written) => {
    expect(formatPercent(percent)).toBe(written);
  });
});

describe('formatRate', () => {
  it('writes a rate with two decimals and no sign', () => {
    expect(formatRate('50.00')).toBe('50,00%');
    expect(formatRate('66.67')).toBe('66,67%');
  });
});

describe('formatRoundedAmount', () => {
  it('writes an aggregate amount without useless decimals, at most two', () => {
    expect(formatRoundedAmount('3')).toBe('3');
    expect(formatRoundedAmount('1234.5')).toBe('1234,5');
    expect(formatRoundedAmount('0.125')).toBe('0,13');
  });
});

describe('formatRoundedResult', () => {
  it('signs a gain and a loss, and leaves an even result without sign', () => {
    expect(formatRoundedResult('15')).toBe('+15');
    expect(formatRoundedResult('-5')).toBe('-5');
    expect(formatRoundedResult('0')).toBe('0');
  });
});

describe('formatUsd', () => {
  it('writes a cost with the cents and the decimals below the cent', () => {
    expect(formatUsd('1.2')).toBe('1,20');
    expect(formatUsd('0')).toBe('0,00');
    expect(formatUsd('0.0031')).toBe('0,0031');
  });
});

describe('formatGain', () => {
  it.each([
    ['2.5', '+2,50'],
    ['-1.2', '-1,20'],
    ['0', '0,00'],
    ['12345.678', '+12.345,68'],
  ])('writes the gain %s with its sign and the cents as %s', (gain, written) => {
    expect(formatGain(gain)).toBe(written);
  });
});

// Proof of ADR formato-dei-prezzi-condiviso: one shared format for every price column.
describe('formatPrice (ADR formato-dei-prezzi-condiviso)', () => {
  it.each([
    ['63996.0322580645161290322580', '63.996,03'],
    ['3000', '3000'],
    ['3150.5', '3150,5'],
    ['1000', '1000'],
    ['1000.005', '1000,01'],
    ['91000.5', '91.000,5'],
    ['999.123456789', '999,123'],
    ['0.5', '0,5'],
    ['0.000123456789', '0,000123457'],
    ['12.3456789', '12,3457'],
    ['0', '0'],
  ])(
    'writes the price %s at two decimals from 1000, at six significant digits below, as %s',
    (price, written) => {
      expect(formatPrice(price)).toBe(written);
    },
  );
});
