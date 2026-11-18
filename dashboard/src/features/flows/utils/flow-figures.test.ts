import { formatReturn } from './flow-figures';

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
