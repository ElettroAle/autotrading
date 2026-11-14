import { formatReturn, returnTone } from './flow-figures';

describe('formatReturn', () => {
  it('shows a positive return with its sign', () => {
    expect(formatReturn('10.00')).toBe('+10,00%');
  });

  it('shows a negative return with its sign', () => {
    expect(formatReturn('-10.00')).toBe('-10,00%');
  });

  it('shows a return of zero without a sign', () => {
    expect(formatReturn('0.00')).toBe('0,00%');
  });

  it('says the return is not available without initial capital', () => {
    expect(formatReturn(null)).toBe('non disponibile');
  });
});

describe('returnTone', () => {
  it.each([
    ['10.00', 'positive'],
    ['0.01', 'positive'],
    ['-0.01', 'negative'],
    ['0.00', 'neutral'],
    [null, 'neutral'],
  ] as const)('the return %s is %s', (percent, tone) => {
    expect(returnTone(percent)).toBe(tone);
  });
});
