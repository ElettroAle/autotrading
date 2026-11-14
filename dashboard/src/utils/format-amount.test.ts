import { formatAmount, formatPercent, formatSignedAmount } from './format-amount';

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
