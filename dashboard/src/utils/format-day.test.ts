import { dayOrNothing, formatDay } from './format-day';

describe('format day', () => {
  it('writes the day of the API in Italian', () => {
    expect(formatDay('2026-12-15')).toBe('15/12/2026');
  });

  it.each([
    ['', undefined],
    [undefined, undefined],
    ['2026-12-15', '2026-12-15'],
  ])('reads the date input %s as %s', (value, day) => {
    expect(dayOrNothing(value)).toBe(day);
  });
});
