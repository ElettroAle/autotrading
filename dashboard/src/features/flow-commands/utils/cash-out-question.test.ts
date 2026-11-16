import { cashOutQuestion, estimatedFreed, hasProfits } from './cash-out-question';

describe('estimatedFreed', () => {
  it.each([
    ['620', '500', '120'],
    ['618.5', '400', '218.5'],
    ['0.3', '0.1', '0.2'],
    ['100.25', '100.05', '0.2'],
    ['500', '512.75', '-12.75'],
  ])('frees %s less %s as %s, digit for digit', (value, capital, freed) => {
    expect(estimatedFreed(value, capital)).toBe(freed);
  });
});

describe('cashOutQuestion', () => {
  it('names one position to close and the amount freed', () => {
    expect(
      cashOutQuestion({ flowName: 'alfa', positions: 1, freed: '120', currency: 'USDC' }),
    ).toBe('Chiudere 1 posizione di alfa e liberare circa 120 USDC?');
  });

  it('counts the positions to close and writes the amount in Italian', () => {
    expect(
      cashOutQuestion({ flowName: 'alfa', positions: 3, freed: '12500.5', currency: 'USDC' }),
    ).toBe('Chiudere 3 posizioni di alfa e liberare circa 12.500,5 USDC?');
  });

  it('asks only to free the amount when there is no position to close', () => {
    expect(
      cashOutQuestion({ flowName: 'alfa', positions: 0, freed: '218', currency: 'USDC' }),
    ).toBe('Liberare circa 218 USDC da alfa?');
  });
});

describe('hasProfits', () => {
  it.each([
    ['620', '500', true],
    ['500.01', '500', true],
    ['500', '500', false],
    ['500.00', '500', false],
    ['460', '500', false],
  ])('a flow worth %s on a capital of %s has profits: %s', (value, capital, expected) => {
    expect(hasProfits(value, capital)).toBe(expected);
  });
});
