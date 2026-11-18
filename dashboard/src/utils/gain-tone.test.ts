import { gainTone } from './gain-tone';

// One colour of a gain or a loss for every result of the dashboard (Bug 601).

describe('gainTone', () => {
  it.each([
    ['10.00', 'text-green-700'],
    ['0.01', 'text-green-700'],
    ['8.927573', 'text-green-700'],
    ['-0.01', 'text-red-700'],
    ['-5.5', 'text-red-700'],
    ['0', 'text-slate-700'],
    ['0.00', 'text-slate-700'],
    ['-0.00', 'text-slate-700'],
  ])('colours the value %s with %s', (value, tone) => {
    expect(gainTone(value)).toBe(tone);
  });

  it('colours a value the API does not give as even', () => {
    expect(gainTone(null)).toBe('text-slate-700');
  });
});
